# jobs.py
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

async def send_reminder_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"💊 Reminder: It's time to take your {job.data}!")
    logger.info(f"Sent reminder for job {job.name} to chat {job.chat_id}")