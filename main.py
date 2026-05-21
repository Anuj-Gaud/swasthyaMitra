# main.py
import logging
import os
import datetime
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler


from database import setup_database, get_all_reminders
from jobs import send_reminder_callback
import handlers
load_dotenv()
BOT_TOKEN=os.getenv("BOT_TOKEN")


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
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

if __name__ == "__main__":
    main()