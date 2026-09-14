import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не найдена переменная окружения BOT_TOKEN")

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Все выгодные", callback_data="all"),
         InlineKeyboardButton("🖥 ПК", callback_data="pc")],
        [InlineKeyboardButton("🎮 Видеокарты", callback_data="gpu"),
         InlineKeyboardButton("💻 Ноутбуки", callback_data="laptop")],
        [InlineKeyboardButton("🖥 Мониторы", callback_data="monitor"),
         InlineKeyboardButton("⚙️ Настройки", callback_data="settings")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>SkupkaPCBot</b>\n\n"
        "Бот для поиска выгодной компьютерной техники.\n\n"
        "📍 Город: <b>Улан-Удэ</b>\n"
        "💰 Ищем варианты с запасом для перепродажи.\n\n"
        "Выбери категорию:",
        parse_mode="HTML", reply_markup=menu())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ <b>SkupkaPCBot</b>\n\n"
        "/start — главное меню\n/settings — настройки\n/help — помощь",
        parse_mode="HTML", reply_markup=menu())

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ <b>Настройки</b>\n\n📍 Город: Улан-Удэ\n"
        "💰 Минимальная прибыль: пока не задана\n"
        "📊 Минимальная оценка: пока не задана",
        parse_mode="HTML", reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    names = {
        "all": "🔎 Все выгодные", "pc": "🖥 Системные блоки",
        "gpu": "🎮 Видеокарты", "laptop": "💻 Ноутбуки",
        "monitor": "🖥 Мониторы", "settings": "⚙️ Настройки"
    }
    title = names.get(q.data, "Раздел")
    await q.edit_message_text(
        f"<b>{title}</b>\n\n"
        "Поиск объявлений пока не подключён.\n"
        "Следующим этапом подключим источник объявлений и фильтр выгодных сделок.",
        parse_mode="HTML", reply_markup=menu())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(buttons))
    print("SkupkaPCBot запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
