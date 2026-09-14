import os
import json
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

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
    "categories": {
        "pc": True,
        "gpu": True,
        "laptop": True,
        "monitor": True,
        "parts": True,
    },
}

# ТЕСТОВЫЕ данные. Это НЕ реальные объявления Avito.
DEMO_LISTINGS = [
    {"id":"demo1","category":"pc","title":"Игровой ПК Ryzen 5 5500 + GTX 1660 Super 32GB","price":28000,"resale":35000,"expenses":700,"new":True},
    {"id":"demo2","category":"gpu","title":"RTX 3060 12GB, отличное состояние","price":22000,"resale":30000,"expenses":500,"new":True},
    {"id":"demo3","category":"laptop","title":"MSI Katana 17, RTX 3050, 16GB","price":45000,"resale":56000,"expenses":1000,"new":True},
    {"id":"demo4","category":"monitor","title":"27 дюймов 165Hz, игровой монитор","price":12000,"resale":15000,"expenses":500,"new":False},
    {"id":"demo5","category":"pc","title":"Офисный ПК i5, 8GB, SSD","price":18000,"resale":21000,"expenses":500,"new":True},
]

def clone_defaults():
    return json.loads(json.dumps(DEFAULTS))

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
        data[key] = clone_defaults()
        save_data(data)
    return data[key]

def put_settings(uid, settings):
    data = load_data()
    data[str(uid)] = settings
    save_data(data)

def money(n):
    return f"{int(n):,}".replace(",", " ") + " ₽"

def settings_text(s):
    return (
        "<b>⚙️ Настройки поиска</b>\n\n"
        f"📍 Город: <b>{s['city']}</b>\n"
        f"💰 Максимальная покупка: <b>{money(s['max_purchase'])}</b>\n"
        f"📈 Минимальная прибыль: <b>{money(s['min_profit'])}</b>\n"
        f"📊 Минимальный ROI: <b>{s['min_roi']}%</b>\n"
        f"⭐ Минимальная оценка: <b>{s['min_score']}/10</b>\n"
        f"🆕 Только новые: <b>{'Да' if s['new_only'] else 'Нет'}</b>\n\n"
        "Нажми параметр и введи новое значение."
    )

def settings_menu(s):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📍 Город: {s['city']}", callback_data="edit_city")],
        [InlineKeyboardButton(f"💰 Макс. покупка: {money(s['max_purchase'])}", callback_data="edit_max")],
        [InlineKeyboardButton(f"📈 Мин. прибыль: {money(s['min_profit'])}", callback_data="edit_profit")],
        [InlineKeyboardButton(f"📊 Мин. ROI: {s['min_roi']}%", callback_data="edit_roi")],
        [InlineKeyboardButton(f"⭐ Мин. оценка: {s['min_score']}/10", callback_data="edit_score")],
        [InlineKeyboardButton(f"{'🟢' if s['new_only'] else '⚪'} Только новые", callback_data="toggle_new")],
        [InlineKeyboardButton("🧩 Категории", callback_data="categories")],
        [InlineKeyboardButton("🔄 Сбросить", callback_data="reset")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="home")],
    ])

def categories_menu(s):
    c = s["categories"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(("✅ " if c["pc"] else "❌ ") + "ПК", callback_data="toggle_cat_pc")],
        [InlineKeyboardButton(("✅ " if c["gpu"] else "❌ ") + "Видеокарты", callback_data="toggle_cat_gpu")],
        [InlineKeyboardButton(("✅ " if c["laptop"] else "❌ ") + "Ноутбуки", callback_data="toggle_cat_laptop")],
        [InlineKeyboardButton(("✅ " if c["monitor"] else "❌ ") + "Мониторы", callback_data="toggle_cat_monitor")],
        [InlineKeyboardButton(("✅ " if c["parts"] else "❌ ") + "Комплектующие", callback_data="toggle_cat_parts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="settings")],
    ])

def score_deal(profit, roi):
    if profit <= 0:
        return 0.0
    score = min(5.0, profit / 2000)
    score += min(4.0, roi / 10)
    if profit >= 10000:
        score += 0.5
    if roi >= 30:
        score += 0.5
    return round(min(10.0, score), 1)

def analyze(item, s):
    profit = item["resale"] - item["price"] - item["expenses"]
    roi = profit / item["price"] * 100 if item["price"] else 0
    score = score_deal(profit, roi)
    passed = (
        item["price"] <= s["max_purchase"]
        and profit >= s["min_profit"]
        and roi >= s["min_roi"]
        and score >= float(s["min_score"])
        and (not s["new_only"] or item["new"])
        and s["categories"].get(item["category"], False)
    )
    return {**item, "profit": profit, "roi": roi, "score": score, "passed": passed}

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Тестовый поиск", callback_data="scan")],
        [InlineKeyboardButton("⚙️ Настройки поиска", callback_data="settings")],
        [InlineKeyboardButton("🖥 ПК", callback_data="cat_pc"),
         InlineKeyboardButton("🎮 Видеокарты", callback_data="cat_gpu")],
        [InlineKeyboardButton("💻 Ноутбуки", callback_data="cat_laptop"),
         InlineKeyboardButton("🖥 Мониторы", callback_data="cat_monitor")],
        [InlineKeyboardButton("🧩 Комплектующие", callback_data="cat_parts")],
    ])

async def start(update, context):
    await update.message.reply_text(
        "👋 <b>SkupkaPCBot v5</b>\n\n"
        "Теперь настройки поиска можно менять прямо из Telegram.\n\n"
        "🔥 <b>Тестовый поиск</b> проверяет фильтры на демонстрационных объявлениях.\n"
        "⚠️ Реальные объявления пока не подключены.",
        parse_mode="HTML", reply_markup=main_menu()
    )

async def settings_cmd(update, context):
    s = get_settings(update.effective_user.id)
    context.user_data.pop("waiting", None)
    await update.message.reply_text(settings_text(s), parse_mode="HTML", reply_markup=settings_menu(s))

async def help_cmd(update, context):
    await update.message.reply_text(
        "📖 <b>Команды</b>\n\n"
        "/start — главное меню\n"
        "/settings — настройки\n"
        "/help — помощь\n\n"
        "Изменяй параметры кнопками, а затем запускай тестовый поиск.",
        parse_mode="HTML", reply_markup=main_menu()
    )

async def text_input(update, context):
    waiting = context.user_data.get("waiting")
    if not waiting:
        return

    uid = update.effective_user.id
    s = get_settings(uid)
    raw = update.message.text.strip()

    try:
        if waiting == "city":
            if len(raw) < 2 or len(raw) > 100:
                raise ValueError
            s["city"] = raw
        else:
            value = float(raw.replace(" ", "").replace(",", "."))
            if waiting == "max":
                if not 0 < value <= 10000000: raise ValueError
                s["max_purchase"] = int(value)
            elif waiting == "profit":
                if not 0 <= value <= 10000000: raise ValueError
                s["min_profit"] = int(value)
            elif waiting == "roi":
                if not 0 <= value <= 1000: raise ValueError
                s["min_roi"] = value if value % 1 else int(value)
            elif waiting == "score":
                if not 0 <= value <= 10: raise ValueError
                s["min_score"] = value if value % 1 else int(value)

        put_settings(uid, s)
        context.user_data.pop("waiting", None)
        await update.message.reply_text(
            "✅ <b>Настройка сохранена.</b>\n\n" + settings_text(s),
            parse_mode="HTML", reply_markup=settings_menu(s)
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Неверное значение.\n"
            "Введи число, например <b>40000</b> или <b>20</b>.",
            parse_mode="HTML"
        )

async def scan(update, context):
    q = update.callback_query
    if q:
        await q.answer()
        send = q.message.reply_text
        uid = q.from_user.id
    else:
        send = update.message.reply_text
        uid = update.effective_user.id

    s = get_settings(uid)
    results = [analyze(x, s) for x in DEMO_LISTINGS]
    good = sorted([x for x in results if x["passed"]],
                  key=lambda x: (x["score"], x["profit"]), reverse=True)

    await send(
        "🔎 <b>Тестовый поиск</b>\n\n"
        f"Проверено: <b>{len(results)}</b>\n"
        f"Подошло: <b>{len(good)}</b>\n"
        f"Фильтр: покупка до {money(s['max_purchase'])}, "
        f"прибыль от {money(s['min_profit'])}, ROI от {s['min_roi']}%",
        parse_mode="HTML"
    )

    if not good:
        await send(
            "😕 <b>Подходящих вариантов нет.</b>\n\n"
            "Попробуй ослабить фильтры в настройках.",
            parse_mode="HTML", reply_markup=main_menu()
        )
        return

    for x in good:
        await send(
            f"🔥 <b>ВЫГОДНЫЙ ВАРИАНТ — {x['score']}/10</b>\n\n"
            f"{x['title']}\n\n"
            f"💰 Покупка: <b>{money(x['price'])}</b>\n"
            f"💵 Продажа: <b>{money(x['resale'])}</b>\n"
            f"📦 Расходы: <b>{money(x['expenses'])}</b>\n"
            f"🟢 Прибыль: <b>{money(x['profit'])}</b>\n"
            f"📊 ROI: <b>{x['roi']:.1f}%</b>\n"
            f"📍 {s['city']}\n\n"
            "⚠️ Демонстрационные данные.",
            parse_mode="HTML"
        )
    await send("Готово. Это был тест фильтра.", reply_markup=main_menu())

async def buttons(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    s = get_settings(uid)
    action = q.data

    if action == "home":
        context.user_data.pop("waiting", None)
        await q.edit_message_text("👋 <b>SkupkaPCBot v5</b>\n\nВыбери действие:",
                                  parse_mode="HTML", reply_markup=main_menu())
        return

    if action == "settings":
        context.user_data.pop("waiting", None)
        await q.edit_message_text(settings_text(s), parse_mode="HTML", reply_markup=settings_menu(s))
        return

    if action == "categories":
        await q.edit_message_text("<b>🧩 Категории поиска</b>\n\nНажимай, чтобы включать или выключать категории.",
                                  parse_mode="HTML", reply_markup=categories_menu(s))
        return

    if action == "toggle_new":
        s["new_only"] = not s["new_only"]
        put_settings(uid, s)
        await q.edit_message_text(settings_text(s), parse_mode="HTML", reply_markup=settings_menu(s))
        return

    if action.startswith("toggle_cat_"):
        key = action.replace("toggle_cat_", "")
        s["categories"][key] = not s["categories"][key]
        put_settings(uid, s)
        await q.edit_message_text("<b>🧩 Категории поиска</b>\n\nНажимай, чтобы включать или выключать категории.",
                                  parse_mode="HTML", reply_markup=categories_menu(s))
        return

    prompts = {
        "edit_city": ("city", "📍 Введи город, например: <b>Улан-Удэ</b>"),
        "edit_max": ("max", "💰 Введи максимальную цену покупки в ₽, например: <b>50000</b>"),
        "edit_profit": ("profit", "📈 Введи минимальную прибыль в ₽, например: <b>7000</b>"),
        "edit_roi": ("roi", "📊 Введи минимальный ROI в %, например: <b>20</b>"),
        "edit_score": ("score", "⭐ Введи минимальную оценку от 0 до 10, например: <b>8</b>"),
    }
    if action in prompts:
        waiting, text = prompts[action]
        context.user_data["waiting"] = waiting
        await q.edit_message_text(text + "\n\nПосле ввода значение сохранится автоматически.",
                                  parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="settings")]]))
        return

    if action == "reset":
        s = clone_defaults()
        put_settings(uid, s)
        await q.edit_message_text("🔄 <b>Настройки сброшены.</b>\n\n" + settings_text(s),
                                  parse_mode="HTML", reply_markup=settings_menu(s))
        return

    if action == "scan":
        await scan(update, context)
        return

    if action.startswith("cat_"):
        names = {"pc":"ПК","gpu":"Видеокарты","laptop":"Ноутбуки","monitor":"Мониторы","parts":"Комплектующие"}
        key = action[4:]
        await q.edit_message_text(
            f"🧩 <b>{names.get(key, key)}</b>\n\n"
            "Для этой категории пока используется общий тестовый поиск.",
            parse_mode="HTML", reply_markup=main_menu()
        )
        return

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))
    print("SkupkaPCBot v5 запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
