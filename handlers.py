# handlers.py
import logging
import os
import datetime
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

import database
import features
import config
import jobs
from jobs import send_reminder_callback

logger = logging.getLogger(__name__)

# --- NEW HELPER FUNCTION ---
async def ask_for_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a message with a button to request the user's location."""
    keyboard = [[KeyboardButton("📍 Share My Location to Find Services", request_location=True)]]
    await update.message.reply_text(
        "For your convenience, I can also find nearby medical facilities for you. Please tap the button below to share your location.",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )

# --- Command Handlers (Unchanged) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("🔍 Check a Symptom", callback_data="start_symptom")], [InlineKeyboardButton("ℹ️ Get Help", callback_data="start_help")]]
    await update.message.reply_text("👋 Welcome! How can I assist?", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("You can ask me about symptoms or drugs. Use commands like:\n/remind <med> at <HH:MM>\n/log <symptom> <severity/10>\n/summary\n/locate")

# ... (log_command, summary_command, remind_command, locate_command are unchanged)
async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        symptom, severity = context.args[0], context.args[1]
        database.log_symptom(update.effective_user.id, symptom, severity)
        await update.message.reply_text(f"Logged: '{symptom}' with severity {severity}.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /log <symptom> <severity e.g., 7/10>")

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    summary_data = database.get_symptom_summary(update.effective_user.id)
    if not summary_data:
        await update.message.reply_text("No symptoms logged recently.")
        return
    message = "Your recent symptom log:\n\n" + "\n".join([f"- *{s}* ({sev}) on {t}" for s, sev, t in summary_data])
    await update.message.reply_markdown(message)

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        medication, time_str = context.args[0], context.args[2]
        reminder_time = datetime.datetime.strptime(time_str, '%H:%M').time()
        job_name = f"reminder_{update.effective_chat.id}_{medication}_{time_str}"
        context.job_queue.run_daily(jobs.send_reminder_callback, time=reminder_time, data=medication, chat_id=update.effective_chat.id, name=job_name)
        database.add_reminder(update.effective_chat.id, medication, time_str, job_name)
        await update.effective_message.reply_text(f"Reminder set for {medication} at {time_str} daily!")
    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /remind <medication> at <HH:MM>")

async def locate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[KeyboardButton("Share My Location", request_location=True)]]
    await update.message.reply_text("Please share your location to find services.", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))


# --- Callback & Message Handlers (Unchanged) ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (this function is unchanged)
    query = update.callback_query
    await query.answer()
    if query.data == 'start_symptom': await query.edit_message_text("Of course. Please describe your symptoms for me.")
    elif query.data == 'start_help': await query.edit_message_text("Ask me about a symptom or use commands like /remind.")
    elif query.data == 'find_hospital':
        await query.edit_message_text("To find a hospital, I need your location.")
        keyboard = [[KeyboardButton("📍 Share My Location", request_location=True)]]
        await query.message.reply_text("Please tap the button below to share your location.",reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))

async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (this function is unchanged)
    query = update.callback_query
    await query.answer()
    logger.info(f"Feedback from {query.from_user.id}: {query.data}")
    await query.edit_message_text("Thank you for your feedback!")

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (this function is unchanged)
    lat, lon = update.message.location.latitude, update.message.location.longitude
    await update.message.reply_text("Searching...", reply_markup=ReplyKeyboardRemove())
    results_message, map_url = features.find_nearby_health_services(lat, lon)
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🗺️ View on Map", url=map_url)]]) if map_url else None
    await update.message.reply_html(results_message, reply_markup=reply_markup)

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (this function is unchanged)
    doc = update.message.document
    await update.message.reply_text(f"Received {doc.file_name}. Reading, please wait...")
    file = await doc.get_file()
    file_path = os.path.join("uploads", f"{uuid.uuid4()}_{doc.file_name}")
    await file.download_to_drive(file_path)
    # ... text extraction logic ...
    await update.message.reply_text("Document processing is under development.")

async def request_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (this function is unchanged)
    keyboard = [[InlineKeyboardButton("👍 ", callback_data="feedback_helpful")], [InlineKeyboardButton("👎 ", callback_data="feedback_not_helpful")]]
    await update.message.reply_text("Was this helpful?", reply_markup=InlineKeyboardMarkup(keyboard))


# --- MODIFIED: Symptom conversation now includes link and location prompt ---
async def handle_symptom_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    state = context.user_data
    lang_pack = features.get_language_pack(state.get('language', 'English'))
    symptom_questions = lang_pack.get("SYMPTOM_QUESTIONS", {})
    
    state.get('answers', []).append(user_message)
    if state.get('question_index') == 0 and 'yes' in user_message.lower():
        await update.message.reply_html(lang_pack["REDIRECT_MESSAGE"])
        await ask_for_location(update, context) # Also ask for location in triage
        state.clear(); return

    current_question_list = symptom_questions.get(state.get('symptom_flow'), {}).get("questions", [])
    if (state.get('question_index', -1) + 1) < len(current_question_list):
        state['question_index'] += 1
        await update.message.reply_text(current_question_list[state['question_index']])
    else:
        summary_template = symptom_questions.get(state.get('symptom_flow'), {}).get("final_summary", "Processing complete.")
        final_summary = summary_template.format(**{f'ans{i+1}': ans for i, ans in enumerate(state.get('answers', []))})
        
        # Add website link and disclaimer before sending
        disclaimer = config.DISCLAIMER_MAP.get(state.get('language'), '').replace('*', '') # Remove markdown for HTML
        final_response = final_summary + config.WEBSITE_LINK_HTML + disclaimer
        
        await update.message.reply_html(final_response)
        await ask_for_location(update, context) # Ask for location after summary
        await request_feedback(update, context)
        state.clear()

# --- MODIFIED: Main message handler now adds link and location prompt to all paths ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text: return
    user_message = update.message.text
    if 'symptom_flow' in context.user_data: await handle_symptom_conversation(update, context); return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    prompt = config.INTENT_PROMPT_TEMPLATE.format(query=user_message, supported_languages=", ".join(config.TRANSLATIONS.keys()))
    language, intent, drug_name, symptom = features.parse_ai_response(features.run_ai_prompt(prompt))
    logger.info(f"AI: Lang={language}, Intent={intent}, Drug={drug_name}, Symptom={symptom}")

    # Path 1: Major Symptom Triage
    triage_result = features.triage_user_input(user_message, language)
    if triage_result:
        await update.message.reply_html(triage_result)
        await ask_for_location(update, context) # Ask for location
        return
        
    lang_pack = features.get_language_pack(language)
    symptom_questions = lang_pack.get("SYMPTOM_QUESTIONS", {})
    minor_diseases = lang_pack.get("MINOR_DISEASES", {})
    disclaimer = config.DISCLAIMER_MAP.get(language, '').replace('*', '') # Remove markdown for HTML

    # Path 2: Symptom Funnel (start)
    if intent == "B" and symptom in symptom_questions:
        context.user_data.update({'language': language, 'symptom_flow': symptom, 'question_index': 0, 'answers': []})
        await update.message.reply_text(symptom_questions[symptom]['questions'][0])
    
    # Path 3: Minor Disease Info
    elif intent == "B" and symptom in minor_diseases:
        response = minor_diseases[symptom]
        if symptom in config.RELIABLE_SOURCES: 
            response += f"<br><br><b>Source:</b> {config.RELIABLE_SOURCES[symptom]}"
        final_response = response + config.WEBSITE_LINK_HTML + disclaimer
        await update.message.reply_html(final_response)
        await ask_for_location(update, context)
        await request_feedback(update, context)
        
    # Path 4: General Fallback
    else:
        fallback_prompt = f"In {language}, provide a brief, helpful, safe response for: '{user_message}'. Do not prescribe."
        response = features.run_ai_prompt(fallback_prompt)
        final_response = response + config.WEBSITE_LINK_HTML + disclaimer
        await update.message.reply_html(final_response)
        await ask_for_location(update, context)
        await request_feedback(update, context)