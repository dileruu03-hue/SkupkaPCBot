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

# Простое локальное хранение настроек по Telegram user_id.
# Позже можно заменить на SQLite/PostgreSQL без изменения интерфейса.
def load_data():
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_data(data):
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def get_settings(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = DEFAULTS.copy()
        data[uid]["categories"] = DEFAULTS["categories"].copy()
        save_data(data)
    return data[uid]

def update_settings(user_id, settings):
    data = load_data()
    data[str(user_id)] = settings
    save_data(data)

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔎 Все выгодные", callback_data="search_all"),
            InlineKeyboardButton("🖥 ПК", callback_data="cat_pc"),
        ],
        [
            InlineKeyboardButton("🎮 Видеокарты", callback_data="cat_gpu"),
            InlineKeyboardButton("💻 Ноутбуки", callback_data="cat_laptop"),
        ],
        [
            InlineKeyboardButton("🖥 Мониторы", callback_data="cat_monitor"),
            InlineKeyboardButton("🧩 Комплектующие", callback_data="cat_parts"),
        ],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")]
    ])

def settings_menu(s):
    def mark(v):
        return "✅" if v else "❌"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📍 Город: {s['city']}", callback_data="set_city")],
        [InlineKeyboardButton(f"💰 Макс. покупка: {s['max_purchase']:,} ₽".replace(",", " "), callback_data="set_max")],
        [InlineKeyboardButton(f"📈 Мин. прибыль: {s['min_profit']:,} ₽".replace(",", " "), callback_data="set_profit")],
        [InlineKeyboardButton(f"📊 Мин. ROI: {s['min_roi']}%", callback_data="set_roi")],
        [InlineKeyboardButton(f"⭐ Мин. оценка: {s['min_score']}/10", callback_data="set_score")],
        [InlineKeyboardButton(f"{mark(s['new_only'])} Только новые объявления", callback_data="toggle_new")],
        [InlineKeyboardButton("🧩 Категории", callback_data="categories")],
        [InlineKeyboardButton("🔄 Сбросить настройки", callback_data="reset")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="home")],
    ])

def categories_menu(s):
    c = s["categories"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(("✅ " if c["pc"] else "❌ ") + "ПК", callback_data="toggle_pc")],
        [InlineKeyboardButton(("✅ " if c["gpu"] else "❌ ") + "Видеокарты", callback_data="toggle_gpu")],
        [InlineKeyboardButton(("✅ " if c["laptop"] else "❌ ") + "Ноутбуки", callback_data="toggle_laptop")],
        [InlineKeyboardButton(("✅ " if c["monitor"] else "❌ ") + "Мониторы", callback_data="toggle_monitor")],
        [InlineKeyboardButton(("✅ " if c["parts"] else "❌ ") + "Комплектующие", callback_data="toggle_parts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="settings")],
    ])

def settings_text(s):
    return (
        "<b>⚙️ Настройки сканера</b>\n\n"
        f"📍 Город: <b>{s['city']}</b>\n"
        f"💰 Максимальная цена покупки: <b>{s['max_purchase']:,} ₽</b>\n"
        f"📈 Минимальная прибыль: <b>{s['min_profit']:,} ₽</b>\n"
        f"📊 Минимальный ROI: <b>{s['min_roi']}%</b>\n"
        f"⭐ Минимальная оценка сделки: <b>{s['min_score']}/10</b>\n"
        f"🆕 Только новые: <b>{'Да' if s['new_only'] else 'Нет'}</b>\n\n"
        "Нажми нужный параметр, чтобы изменить его."
    ).replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>SkupkaPCBot v3</b>\n\n"
        "Настрой сканер под свою перепродажу.\n\n"
        "📍 По умолчанию: <b>Улан-Удэ</b>\n"
        "💰 Покупка до: <b>50 000 ₽</b>\n"
        "📈 Прибыль от: <b>5 000 ₽</b>\n"
        "📊 ROI от: <b>15%</b>\n"
        "⭐ Оценка от: <b>7/10</b>",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_settings(update.effective_user.id)
    context.user_data.pop("waiting_for", None)
    await update.message.reply_text(
        settings_text(s), parse_mode="HTML", reply_markup=settings_menu(s)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ <b>SkupkaPCBot v3</b>\n\n"
        "/start — главное меню\n"
        "/settings — настройки\n"
        "/help — помощь\n\n"
        "Настройки сохраняются отдельно для твоего Telegram-аккаунта.",
        parse_mode="HTML", reply_markup=main_menu()
    )

async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    waiting = context.user_data.get("waiting_for")
    if not waiting:
        return

    s = get_settings(update.effective_user.id)
    text = update.message.text.strip().replace(" ", "").replace(",", ".")
    try:
        if waiting == "city":
            if len(text) < 2:
                raise ValueError
            s["city"] = update.message.text.strip()
        else:
            value = float(text)
            if waiting == "max":
                if value <= 0 or value > 10000000: raise ValueError
                s["max_purchase"] = int(value)
            elif waiting == "profit":
                if value < 0 or value > 10000000: raise ValueError
                s["min_profit"] = int(value)
            elif waiting == "roi":
                if value < 0 or value > 1000: raise ValueError
                s["min_roi"] = int(value)
            elif waiting == "score":
                if value < 0 or value > 10: raise ValueError
                s["min_score"] = value if value % 1 else int(value)
        update_settings(update.effective_user.id, s)
        context.user_data.pop("waiting_for", None)
        await update.message.reply_text(
            "✅ Настройка сохранена.\n\n" + settings_text(s),
            parse_mode="HTML", reply_markup=settings_menu(s)
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Не удалось распознать значение.\n"
            "Попробуй ещё раз одним числом, например: <b>30000</b>",
            parse_mode="HTML"
        )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    s = get_settings(uid)
    action = q.data

    if action == "home":
        context.user_data.pop("waiting_for", None)
        await q.edit_message_text(
            "👋 <b>SkupkaPCBot v3</b>\n\nВыбери действие:",
            parse_mode="HTML", reply_markup=main_menu()
        )
        return

    if action == "settings":
        context.user_data.pop("waiting_for", None)
        await q.edit_message_text(
            settings_text(s), parse_mode="HTML", reply_markup=settings_menu(s)
        )
        return

    if action == "categories":
        await q.edit_message_text(
            "<b>🧩 Категории поиска</b>\n\n"
            "Нажми на категорию, чтобы включить или выключить её.",
            parse_mode="HTML", reply_markup=categories_menu(s)
        )
        return

    if action.startswith("toggle_"):
        key = action.replace("toggle_", "")
        if key == "new":
            s["new_only"] = not s["new_only"]
            update_settings(uid, s)
            await q.edit_message_text(
                settings_text(s), parse_mode="HTML", reply_markup=settings_menu(s)
            )
            return
        if key in s["categories"]:
            s["categories"][key] = not s["categories"][key]
            update_settings(uid, s)
            await q.edit_message_text(
                "<b>🧩 Категории поиска</b>\n\n"
                "Нажми на категорию, чтобы включить или выключить её.",
                parse_mode="HTML", reply_markup=categories_menu(s)
            )
            return

    input_map = {
        "set_city": ("city", "Напиши город. Например: <b>Улан-Удэ</b>"),
        "set_max": ("max", "Введи максимальную цену покупки в ₽. Например: <b>50000</b>"),
        "set_profit": ("profit", "Введи минимальную чистую прибыль в ₽. Например: <b>5000</b>"),
        "set_roi": ("roi", "Введи минимальный ROI в %. Например: <b>15</b>"),
        "set_score": ("score", "Введи минимальную оценку от 0 до 10. Например: <b>7</b>"),
    }
    if action in input_map:
        waiting, prompt = input_map[action]
        context.user_data["waiting_for"] = waiting
        await q.edit_message_text(
            f"✏️ {prompt}\n\nПосле ввода значения настройки сохранятся автоматически.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="settings")]
            ])
        )
        return

    if action == "reset":
        s = {
            "city": DEFAULTS["city"],
            "max_purchase": DEFAULTS["max_purchase"],
            "min_profit": DEFAULTS["min_profit"],
            "min_roi": DEFAULTS["min_roi"],
            "min_score": DEFAULTS["min_score"],
            "new_only": DEFAULTS["new_only"],
            "categories": DEFAULTS["categories"].copy(),
        }
        update_settings(uid, s)
        await q.edit_message_text(
            "🔄 <b>Настройки сброшены.</b>\n\n" + settings_text(s),
            parse_mode="HTML", reply_markup=settings_menu(s)
        )
        return

    if action.startswith("cat_") or action == "search_all":
        labels = {
            "search_all": "🔎 Все выгодные",
            "cat_pc": "🖥 ПК",
            "cat_gpu": "🎮 Видеокарты",
            "cat_laptop": "💻 Ноутбуки",
            "cat_monitor": "🖥 Мониторы",
            "cat_parts": "🧩 Комплектующие",
        }
        await q.edit_message_text(
            f"<b>{labels.get(action, 'Поиск')}</b>\n\n"
            "⏳ Поиск объявлений пока не подключён.\n\n"
            "Настройки уже готовы. Следующим этапом подключим источник объявлений и расчёт выгодности.",
            parse_mode="HTML", reply_markup=main_menu()
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))
    print("SkupkaPCBot v3 запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
