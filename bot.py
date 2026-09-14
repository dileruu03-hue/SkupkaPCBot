import os
import json
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не найдена переменная окружения BOT_TOKEN")

DATA_FILE = Path("settings.json")

DEFAULTS = {
    "city": "Улан-Удэ",
    "max_purchase": 50000,
    "min_profit": 5000,
    "min_roi": 15,
    "min_score": 7,
    "new_only": True,
    "categories": {"pc": True, "gpu": True, "laptop": True, "monitor": True, "parts": True},
}

# Тестовые объявления для проверки "мозга" сканера.
# Реальный источник объявлений подключим отдельным модулем позже.
DEMO_LISTINGS = [
    {"id":"demo1","category":"pc","title":"Игровой ПК Ryzen 5 5500 + GTX 1660 Super 32GB","price":28000,
     "resale":35000,"expenses":700,"new":True,"url":"https://www.avito.ru/"},
    {"id":"demo2","category":"gpu","title":"RTX 3060 12GB, отличное состояние","price":22000,
     "resale":27000,"expenses":500,"new":True,"url":"https://www.avito.ru/"},
    {"id":"demo3","category":"laptop","title":"MSI Katana 17, i5/RTX 3050, 16GB","price":45000,
     "resale":52000,"expenses":1000,"new":True,"url":"https://www.avito.ru/"},
    {"id":"demo4","category":"monitor","title":"27 дюймов 165Hz, игровой монитор","price":12000,
     "resale":14500,"expenses":500,"new":False,"url":"https://www.avito.ru/"},
    {"id":"demo5","category":"pc","title":"Офисный ПК i5, 8GB, SSD","price":18000,
     "resale":19000,"expenses":500,"new":True,"url":"https://www.avito.ru/"},
]

def load_data():
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_settings(uid):
    data = load_data()
    key = str(uid)
    if key not in data:
        data[key] = json.loads(json.dumps(DEFAULTS))
        save_data(data)
    return data[key]

def money(n):
    return f"{int(n):,}".replace(",", " ") + " ₽"

def score_deal(price, profit, roi):
    # Оценка 0-10: прибыль + ROI, с бонусом за большой абсолютный запас.
    if profit <= 0:
        return 0
    score = 0
    score += min(5, profit / 2000)
    score += min(4, roi / 10)
    if profit >= 10000:
        score += 0.5
    if roi >= 30:
        score += 0.5
    return round(min(10, score), 1)

def analyze(item, s):
    profit = item["resale"] - item["price"] - item["expenses"]
    roi = (profit / item["price"] * 100) if item["price"] else 0
    score = score_deal(item["price"], profit, roi)
    passed = (
        item["price"] <= s["max_purchase"] and
        profit >= s["min_profit"] and
        roi >= s["min_roi"] and
        score >= float(s["min_score"]) and
        (not s["new_only"] or item["new"]) and
        s["categories"].get(item["category"], False)
    )
    return {**item, "profit": profit, "roi": roi, "score": score, "passed": passed}

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Тест поиска", callback_data="scan"),
         InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("🖥 ПК", callback_data="cat_pc"),
         InlineKeyboardButton("🎮 Видеокарты", callback_data="cat_gpu")],
        [InlineKeyboardButton("💻 Ноутбуки", callback_data="cat_laptop"),
         InlineKeyboardButton("🖥 Мониторы", callback_data="cat_monitor")],
        [InlineKeyboardButton("🧩 Комплектующие", callback_data="cat_parts")],
    ])

def settings_menu(s):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📍 Город: {s['city']}", callback_data="noop")],
        [InlineKeyboardButton(f"💰 Макс. покупка: {money(s['max_purchase'])}", callback_data="noop")],
        [InlineKeyboardButton(f"📈 Мин. прибыль: {money(s['min_profit'])}", callback_data="noop")],
        [InlineKeyboardButton(f"📊 Мин. ROI: {s['min_roi']}%", callback_data="noop")],
        [InlineKeyboardButton(f"⭐ Мин. оценка: {s['min_score']}/10", callback_data="noop")],
        [InlineKeyboardButton("🔎 Запустить тестовый поиск", callback_data="scan")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="home")],
    ])

async def start(update, context):
    await update.message.reply_text(
        "👋 <b>SkupkaPCBot v4</b>\n\n"
        "🔥 Теперь у бота есть тестовый анализатор выгодности.\n\n"
        "Нажми <b>«🔥 Тест поиска»</b> — бот возьмёт тестовые объявления, "
        "рассчитает прибыль, ROI и оценку и покажет только прошедшие фильтр.",
        parse_mode="HTML", reply_markup=menu())

async def settings_cmd(update, context):
    s = get_settings(update.effective_user.id)
    await update.message.reply_text(
        "<b>⚙️ Текущие настройки</b>\n\n"
        f"📍 Город: {s['city']}\n"
        f"💰 Макс. покупка: {money(s['max_purchase'])}\n"
        f"📈 Мин. прибыль: {money(s['min_profit'])}\n"
        f"📊 Мин. ROI: {s['min_roi']}%\n"
        f"⭐ Мин. оценка: {s['min_score']}/10\n"
        f"🆕 Только новые: {'Да' if s['new_only'] else 'Нет'}\n\n"
        "Изменение настроек оставлено из v3; они продолжают работать.",
        parse_mode="HTML", reply_markup=settings_menu(s))

async def scan(update, context):
    q = update.callback_query
    if q:
        await q.answer()
        uid = q.from_user.id
        send = q.message.reply_text
    else:
        uid = update.effective_user.id
        send = update.message.reply_text

    s = get_settings(uid)
    results = [analyze(x, s) for x in DEMO_LISTINGS]
    good = [x for x in results if x["passed"]]
    good.sort(key=lambda x: (x["score"], x["profit"]), reverse=True)

    await send(
        f"🔎 <b>Тестовый поиск завершён</b>\n\n"
        f"Проверено: <b>{len(results)}</b>\n"
        f"Прошли фильтр: <b>{len(good)}</b>\n"
        f"📍 {s['city']}",
        parse_mode="HTML"
    )

    if not good:
        await send("😕 Подходящих тестовых объявлений нет.\nПопробуй снизить фильтры в настройках.", reply_markup=menu())
        return

    for x in good:
        await send(
            f"🔥 <b>ВЫГОДНЫЙ ВАРИАНТ — {x['score']}/10</b>\n\n"
            f"🖥 {x['title']}\n"
            f"💰 Покупка: <b>{money(x['price'])}</b>\n"
            f"💵 Продажа: <b>{money(x['resale'])}</b>\n"
            f"📦 Расходы: <b>{money(x['expenses'])}</b>\n"
            f"🟢 Чистая прибыль: <b>{money(x['profit'])}</b>\n"
            f"📊 ROI: <b>{x['roi']:.1f}%</b>\n\n"
            f"📍 {s['city']}\n"
            f"⚠️ Это тестовое объявление — ссылка демонстрационная.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Открыть объявление", url=x["url"])]
            ])
        )

async def buttons(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "scan":
        await scan(update, context)
        return
    if q.data == "settings":
        s = get_settings(q.from_user.id)
        await q.edit_message_text(
            f"<b>⚙️ Настройки</b>\n\n"
            f"📍 Город: {s['city']}\n"
            f"💰 Макс. покупка: {money(s['max_purchase'])}\n"
            f"📈 Мин. прибыль: {money(s['min_profit'])}\n"
            f"📊 Мин. ROI: {s['min_roi']}%\n"
            f"⭐ Мин. оценка: {s['min_score']}/10",
            parse_mode="HTML", reply_markup=settings_menu(s))
        return
    if q.data == "home":
        await q.edit_message_text("👋 <b>SkupkaPCBot v4</b>\n\nВыбери действие:", parse_mode="HTML", reply_markup=menu())
        return
    if q.data.startswith("cat_"):
        cat = q.data[4:]
        s = get_settings(q.from_user.id)
        names = {"pc":"ПК","gpu":"Видеокарты","laptop":"Ноутбуки","monitor":"Мониторы","parts":"Комплектующие"}
        s["categories"][cat] = True
        save_data({**load_data(), str(q.from_user.id): s})
        await q.edit_message_text(
            f"🧩 Категория <b>{names.get(cat, cat)}</b> включена.\n\n"
            "Для проверки всех категорий запусти «🔥 Тест поиска».",
            parse_mode="HTML", reply_markup=menu())
        return

async def help_cmd(update, context):
    await update.message.reply_text(
        "v4 добавляет тестовый модуль анализа: прибыль, ROI, оценка 0–10 и фильтрацию по твоим настройкам.\n\n"
        "Реальный источник объявлений подключается отдельно.",
        reply_markup=menu())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()

if __name__ == "__main__":
    main()
