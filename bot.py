import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 SkupkaPCBot запущен!\n\n"
        "Это первая версия. Команды:\n"
        "/start — меню\n"
        "/settings — настройки\n"
        "/help — помощь\n\n"
        "Следующим этапом подключим мониторинг выгодных объявлений."
    )
    await update.message.reply_text(text)

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ Настройки пока базовые.\n\n"
        "Город: Улан-Удэ\n"
        "Валюта: ₽\n"
        "Режим: поиск выгодных объявлений\n\n"
        "Авито-мониторинг будет подключён следующим этапом."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 SkupkaPCBot\n\n"
        "Бот предназначен для поиска потенциально выгодных предложений "
        "компьютерной техники для дальнейшей перепродажи.\n\n"
        "Пока доступен тестовый режим."
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("help", help_cmd))
    logging.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
