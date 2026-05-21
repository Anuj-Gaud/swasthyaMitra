# main.py
import logging
import os
import datetime
import threading
from dotenv import load_dotenv
from flask import Flask
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from database import setup_database, get_all_reminders
from jobs import send_reminder_callback
import handlers

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Tiny Flask server to satisfy Render's port binding requirement ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

@app.route("/health")
def health():
    return {"status": "ok"}, 200


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def run_bot() -> None:
    setup_database()
    os.makedirs("uploads", exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()

    # Reschedule reminders on startup
    for chat_id, medication, time_str, job_name in get_all_reminders():
        reminder_time = datetime.datetime.strptime(time_str, '%H:%M').time()
        application.job_queue.run_daily(send_reminder_callback, time=reminder_time, data=medication, chat_id=chat_id, name=job_name)
    logger.info(f"Rescheduled {len(get_all_reminders())} reminders.")

    # Register all handlers
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("log", handlers.log_command))
    application.add_handler(CommandHandler("summary", handlers.summary_command))
    application.add_handler(CommandHandler("remind", handlers.remind_command))
    application.add_handler(CommandHandler("locate", handlers.locate_command))

    application.add_handler(CallbackQueryHandler(handlers.button_handler))
    application.add_handler(MessageHandler(filters.LOCATION, handlers.location_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, handlers.document_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))

    logger.info("Bot is running...")
    application.run_polling()


def main() -> None:
    # Run Flask in a background thread so Render sees an open port
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Run the bot on the main thread (required by python-telegram-bot)
    run_bot()


if __name__ == "__main__":
    main()
