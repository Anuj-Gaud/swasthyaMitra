# -*- coding: utf-8 -*-

"""
A multi-lingual Telegram health bot that uses OpenRouter.ai for intent classification
and response generation, and provides information from the OpenFDA database.
Includes an enhanced triage system and an interactive symptom funnel for common conditions.
"""

import logging
import os
import requests
from typing import Dict, Tuple, Optional

from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction, ParseMode
from dotenv import load_dotenv
from langdetect import detect, LangDetectException

# =================================================================================
# 1. CONSTANTS AND CONFIGURATION
# =================================================================================

FDA_API_URL = "https://api.fda.gov/drug/label.json"
OPENROUTER_MODEL_NAME = "openai/gpt-3.5-turbo"
WEBSITE_URL = "https://health-ai-assistant-a1af8fd6.base44.app"

# --- Enhanced Triage System Constants ---
MAJOR_SYMPTOMS = [
    # ... [The comprehensive list of major symptoms remains here, unchanged] ...
    # Cardiovascular (Heart-related)
    "chest pain", "crushing pain", "tightness in chest", "chest pressure",
    "pain radiating", "pain in arm or jaw", "pain in shoulder",
    # Respiratory (Breathing-related)
    "can't breathe", "difficulty breathing", "shortness of breath", "gasping for air",
    "choking", "wheezing", "bluish lips", "blue skin", "cyanosis",
    # Neurological (Brain & Nerve-related)
    "sudden numbness", "weakness in limb", "face drooping", "one side weak",
    "sudden confusion", "disoriented", "trouble speaking", "slurred speech",
    "severe headache", "worst headache of my life", "thunderclap headache",
    "seizure", "convulsion", "loss of consciousness", "fainting",
    "sudden vision loss", "double vision", "loss of balance", "trouble walking",
    "head injury with confusion", "head injury with vomiting",
    # Hemorrhagic & Gastrointestinal (Bleeding & Abdominal)
    "severe bleeding", "uncontrolled bleeding", "bleeding that won't stop",
    "severe abdominal pain", "unbearable stomach pain", "rigid belly",
    "vomiting blood", "coffee ground vomit",
    "black stool", "tarry stool", "maroon stool", "blood in stool",
    # Trauma & Injury
    "major injury", "car accident", "fall from height",
    "severe burn", "large burn", "chemical burn", "electrical burn",
    "broken bone", "bone sticking out", "obvious deformity",
    # Anaphylaxis & Allergic Reaction
    "allergic reaction", "swollen tongue", "difficulty swallowing", "hives all over",
    "throat closing", "rapidly spreading rash", "hoarse voice after sting",
    # Mental Health Crisis
    "suicidal", "want to harm myself", "end my life",
    "overdose", "took too many pills",
    # Other High--Risk Symptoms
    "high fever with stiff neck",
    "sudden testicular pain",
    "bleeding while pregnant",
]

### NEW ###
# --- Major Disease First-Aid Guidance ---
# This dictionary maps keywords to brief, safe, immediate actions the user can take
# before they are redirected to seek professional help.
MAJOR_DISEASE_GUIDANCE = {
    "chest pain": "For any chest pain, it's safest to stop all activity and rest in a comfortable position immediately. Loosen any tight clothing.",
    "breathing": "If you or someone else is having difficulty breathing, try to stay calm and sit upright in a comfortable position. Do not lie down, as this can make breathing harder.",
    "bleeding": "For severe bleeding, apply firm, direct pressure to the wound using a clean cloth or bandage. If possible, elevate the injured limb above the heart.",
    "numbness": "If you notice sudden numbness, weakness, or face drooping, it's crucial not to ignore it. Note the time the symptoms first appeared, as this is vital information for medical professionals.",
    "seizure": "If someone is having a seizure, gently guide them to the floor and turn them onto their side to help them breathe. Clear the area of hard or sharp objects. Do not restrain them or put anything in their mouth.",
    "burn": "For a severe burn, immediately run cool (not cold) water over the area for 10-20 minutes. Do not use ice, butter, or ointments. Cover the burn with a sterile, non-adhesive bandage or a clean cloth.",
    "allergic reaction": "For a severe allergic reaction with swelling or trouble breathing, use an epinephrine auto-injector (like an EpiPen) if available. Call for emergency help immediately.",
    "suicidal": "If you are having thoughts of harming yourself, please know that your life is valuable and help is available. It's important to talk to someone right away."
}

# --- Symptom Funnel Questions with Integrated Triage ---
SYMPTOM_QUESTIONS = {
    # ... [The existing SYMPTOM_QUESTIONS dictionary remains here, unchanged] ...
    "headache": {
        "questions": [
            "I can provide general information on headaches. First, to be safe, are you experiencing any of these: the worst headache of your life, a sudden 'thunderclap' onset, fever, stiff neck, confusion, or weakness? (yes/no)",
            "How would you describe the pain? For example: a dull, constant ache or a sharp, throbbing pain?",
            "Are you also feeling sensitive to light or sound?"
        ],
        "final_summary": (
            "Thank you for the information. Based on what you've described (description: {ans2}, sensitivity: {ans3}), here is some general advice:\n\n"
            "• **Rest & Hydration:** Resting in a quiet, dark room and drinking water often helps.\n"
            "• **OTC Options:** For dull, tension-type aches, over-the-counter pain relievers like paracetamol or ibuprofen are commonly used. For throbbing pain with light sensitivity, it's more important to see a doctor for guidance.\n\n"
            "This information is not a medical diagnosis. Please consult a doctor for proper advice."
        )
    },
    "cough": {
        "questions": [
            "Okay, I can help with a cough. Just to be safe, are you also having any significant chest pain or difficulty breathing? (yes/no)",
            "Is the cough 'dry' (no mucus) or 'wet' (with mucus/phlegm)?",
            "Do you also have a sore throat or a runny nose?"
        ],
        "final_summary": (
            "Got it. For a {ans2} cough with {ans3} as another symptom:\n\n"
            "• **Stay Hydrated:** Drinking warm liquids like tea with honey or broth can soothe the throat.\n"
            "• **Humidify the Air:** Using a humidifier or taking a steamy shower can ease irritation.\n"
            "• **OTC Options:** A pharmacist can advise on 'cough suppressants' for dry coughs or 'expectorants' for wet coughs.\n\n"
            "This information is not a medical diagnosis. If symptoms persist, please see a doctor."
        )
    },
    "stomach pain": {
        "questions": [
            "Before I continue, I need to ask a few safety questions. Is the pain severe and unbearable? Is your belly hard to the touch, or have you noticed any blood in your vomit or stool? (yes/no)",
            "Can you describe the pain? Is it a sharp, crampy, or burning feeling?",
            "Is the pain all over, or can you point to one specific area?"
        ],
        "final_summary": (
            "Thank you. For stomach pain described as '{ans2}' and located '{ans3}', here is some general advice:\n\n"
            "• **Diet:** Try sticking to bland foods like bananas, rice, or toast and avoid spicy or fatty foods.\n"
            "• **Hydration:** Sip water or clear broths throughout the day.\n"
            "• **OTC Options:** For burning pain, antacids may offer relief. For cramps, a heating pad might help.\n\n"
            "This is not a diagnosis. Severe or persistent pain always requires a doctor's evaluation."
        )
    },
    "rash": {
        "questions": [
            "Is the rash spreading very quickly? Most importantly, are you also experiencing any swelling in your face or tongue, or having any difficulty breathing? (yes/no)",
            "How would you describe the rash? For example: red bumps, blisters, or flat spots?",
            "Is the rash itchy?"
        ],
        "final_summary": (
            "Understood. For a rash with an appearance of '{ans2}' that is '{ans3}':\n\n"
            "• **Avoid Irritants:** Try not to scratch the area and wear loose-fitting clothing.\n"
            "• **Cool Compress:** Applying a cool, damp cloth can help soothe itching.\n"
            "• **OTC Options:** For itching, over-the-counter hydrocortisone creams or antihistamine pills can be helpful. Please ask a pharmacist for advice.\n\n"
            "This is not a diagnosis. If the rash worsens or doesn't improve, see a doctor."
        )
    }
}

# --- Minor Disease Information ---
MINOR_DISEASES = {
    # ... [The existing MINOR_DISEASES dictionary remains here, unchanged] ...
    # Respiratory Issues 🤧
    "common cold": "The common cold is a viral infection of the nose and throat. General advice includes getting plenty of rest, staying hydrated, and using over-the-counter remedies to manage symptoms like congestion or a runny nose.",
    "allergies": "Allergies, or hay fever, can cause cold-like symptoms like sneezing and a runny nose. The best course of action is to identify and avoid your triggers. Over-the-counter antihistamines may also provide relief.",
    "sinusitis": "Sinusitis, or a sinus infection, is inflammation of the cavities around your nasal passages. Using a saline nasal spray, applying a warm compress to your face, and staying hydrated can help relieve discomfort.",

    # Digestive Problems 🍽️
    "indigestion": "Indigestion can cause discomfort in the upper abdomen. It often helps to eat smaller, more frequent meals and to avoid fatty or spicy foods. Over-the-counter antacids may also be useful.",
    "constipation": "Constipation involves infrequent or difficult bowel movements. Increasing your intake of fiber and water, along with regular exercise, can often help manage it.",
    "diarrhea": "For diarrhea, it's crucial to stay hydrated by drinking plenty of water, broth, or rehydration solutions. Sticking to a bland diet (like bananas, rice, toast) for a short time is also recommended.",

    # Skin Conditions 🤚
    "acne": "Acne is a common skin condition caused by clogged follicles. Keeping your skin clean with a gentle cleanser and using over-the-counter products containing benzoyl peroxide or salicylic acid can be effective.",
    "sunburn": "For a mild sunburn, cool the skin with a damp cloth or cool bath, apply a moisturizer like aloe vera, and drink extra water. Over-the-counter pain relievers can help with discomfort.",
    "athletes foot": "Athlete's foot is a fungal infection. Keeping your feet clean and dry and using over-the-counter antifungal powders or creams are the primary treatments.",

    # General Aches & Pains 🤕
    "muscle strain": "For a minor muscle strain, the R.I.C.E. method is recommended: Rest the affected area, apply Ice, use Compression (like an elastic bandage), and Elevate the limb.",
    "canker sore": "Canker sores are small ulcers inside the mouth. They usually heal on their own in a week or two. Rinsing with salt water and avoiding spicy or acidic foods can reduce irritation."
}

# (All your other constant maps like LANGUAGE_MAP, DISCLAIMER_MAP, etc. go here)
# ... [Unchanged section] ...
LANGUAGE_MAP = {
    'en': 'English', 'hi': 'Hindi', 'bn': 'Bengali', 'te': 'Telugu',
    'mr': 'Marathi', 'ta': 'Tamil', 'gu': 'Gujarati', 'kn': 'Kannada',
    'or': 'Odia', 'ml': 'Malayalam', 'pa': 'Punjabi'
}

REDIRECT_MESSAGE_MAP = {
    'English': (
        f"Based on your symptoms, it's crucial to consult a medical professional immediately. "
        f"My capabilities are limited, and I cannot provide a medical diagnosis.\n\n"
        f"<b>Please find resources on our <a href='{WEBSITE_URL}'>official health portal</a>.</b>\n\n"
        f"<i>If this is a medical emergency, please call your local emergency services immediately.</i>"
    ),   # ... other languages
}

DISCLAIMER_MAP = {
    'English': f"\n\n---\n*⚠️ IMPORTANT: I am an AI assistant, not a doctor. This information is for educational purposes only. You MUST consult a qualified healthcare professional for any medical concerns or before taking any medication.*\n\nFor more resources, visit: {WEBSITE_URL}",
    # ... other languages
}

INTENT_PROMPT_TEMPLATE = """
Analyze the user's query which is in {language}: "{query}"
What is the user's primary intent? Choose one:
A) Asking for information about a specific DRUG.
B) Asking a general question about a single SYMPTOM or CONDITION (e.g., headache, cough, fever, stomach pain, rash, acne).
C) Listing multiple SYMPTOMS to understand potential related health topics.

If the intent is (A), also extract the drug name in ENGLISH.
If the intent is (B), also extract the single symptom in ENGLISH (e.g., headache, cough, acne).

Respond in this exact format:
Intent: [A, B, or C]
Drug Name: [drug name in ENGLISH or "N/A"]
Symptom: [symptom in ENGLISH or "N/A"]
"""

# =================================================================================
# 2. SETUP AND INITIALIZATION
# =================================================================================
# ... [Unchanged section] ...
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    logger.critical("OPENROUTER_API_KEY not found in environment variables. Bot cannot start.")
    exit()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# =================================================================================
# 3. API AND HELPER FUNCTIONS
# =================================================================================
# ... [Unchanged section] ...
def run_ai_prompt(prompt: str) -> str:
    """
    Sends a prompt to the OpenRouter.ai API and returns the response text.
    """
    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error in run_ai_prompt: {e}")
        return "Sorry, I couldn't process your request at the moment."

# =================================================================================
# 4. CORE LOGIC FOR HANDLING QUERIES
# =================================================================================

### MODIFIED ###
def triage_user_input(user_message: str, language: str) -> Optional[str]:
    """
    Checks user message for major symptoms. If found, returns first-aid advice
    followed by a redirect message. Otherwise, returns None.
    """
    normalized_message = user_message.lower()
    redirect_message = REDIRECT_MESSAGE_MAP.get(language, REDIRECT_MESSAGE_MAP['English'])

    # Find the first matching major symptom
    for keyword in MAJOR_SYMPTOMS:
        if keyword in normalized_message:
            logger.warning(f"MAJOR SYMPTOM DETECTED: '{keyword}' in user message. Triggering redirect.")

            # Find the appropriate first-aid guidance
            first_aid = ""
            if "chest pain" in keyword:
                first_aid = MAJOR_DISEASE_GUIDANCE.get("chest pain", "")
            elif "breathing" in keyword:
                first_aid = MAJOR_DISEASE_GUIDANCE.get("breathing", "")
            elif "bleeding" in keyword:
                first_aid = MAJOR_DISEASE_GUIDANCE.get("bleeding", "")
            elif "numbness" in keyword or "drooping" in keyword:
                first_aid = MAJOR_DISEASE_GUIDANCE.get("numbness", "")
            elif "seizure" in keyword:
                first_aid = MAJOR_DISEASE_GUIDANCE.get("seizure", "")
            elif "burn" in keyword:
                first_aid = MAJOR_DISEASE_GUIDANCE.get("burn", "")
            elif "allergic" in keyword or "swollen" in keyword:
                first_aid = MAJOR_DISEASE_GUIDANCE.get("allergic reaction", "")
            elif "suicidal" in keyword:
                first_aid = MAJOR_DISEASE_GUIDANCE.get("suicidal", "")

            # Combine the first-aid tip with the redirect message
            if first_aid:
                return f"{first_aid}\n\n---\n\n{redirect_message}"
            else:
                return redirect_message

    return None

def _get_language_details(query: str) -> Tuple[str, str]:
    try:
        lang_code = detect(query)
        language = LANGUAGE_MAP.get(lang_code, 'English')
    except LangDetectException:
        language = 'English'
    disclaimer = DISCLAIMER_MAP.get(language, DISCLAIMER_MAP['English'])
    return language, disclaimer

def _parse_intent(response_text: str) -> Tuple[str, str, str]:
    # ... [Unchanged section] ...
    intent = "C"
    drug_name = "N/A"
    symptom = "N/A"
    lines = response_text.strip().split('\n')
    for line in lines:
        if "Intent:" in line:
            if "A" in line: intent = "A"
            elif "B" in line: intent = "B"
        if "Drug Name:" in line:
            parts = line.split("Drug Name:")
            if len(parts) > 1: drug_name = parts[1].strip().strip('"')
        if "Symptom:" in line:
            parts = line.split("Symptom:")
            if len(parts) > 1:
                symptom_text = parts[1].strip().lower().strip()
                if "stomach" in symptom_text or "belly" in symptom_text:
                    symptom = "stomach pain"
                elif "athlete" in symptom_text:
                    symptom = "athletes foot"
                else:
                    symptom = symptom_text
    return intent, drug_name, symptom

# =================================================================================
# 5. TELEGRAM BOT HANDLERS
# =================================================================================
# ... [start_command, help_command, handle_symptom_conversation are unchanged] ...
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "👋 Welcome to the Health Bot!\n\nYou can ask me about symptoms, medications, or health topics. Type your question to get started."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the /help command is issued."""
    await update.message.reply_text(
        "ℹ️ *Help*\n\nYou can ask questions like:\n- What are the side effects of paracetamol?\n- I have a headache, what should I do?\n- I have cough and fever.\n\nFor emergencies, always contact a medical professional.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_symptom_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the back-and-forth of the symptom question funnel and triage."""
    user_message = update.message.text

    symptom_flow = context.user_data['symptom_flow']
    question_index = context.user_data['question_index']
    answers = context.user_data['answers']
    language = context.user_data['language']
    disclaimer = context.user_data['disclaimer']

    answers.append(user_message)

    if question_index == 0:
        first_answer = user_message.lower()
        if 'yes' in first_answer or 'yeah' in first_answer or 'yep' in first_answer:
            logger.warning(f"User answered YES to triage question for '{symptom_flow}'. Redirecting.")
            redirect_message = REDIRECT_MESSAGE_MAP.get(language, REDIRECT_MESSAGE_MAP['English'])
            await update.message.reply_text(redirect_message, parse_mode=ParseMode.MARKDOWN)
            context.user_data.clear()
            return

    current_question_list = SYMPTOM_QUESTIONS[symptom_flow]['questions']
    if (question_index + 1) < len(current_question_list):
        next_question_index = question_index + 1
        next_question = current_question_list[next_question_index]
        await update.message.reply_text(next_question)
        context.user_data['question_index'] = next_question_index
    else:
        summary_template = SYMPTOM_QUESTIONS[symptom_flow]['final_summary']
        answer_dict = {f'ans{i+1}': ans for i, ans in enumerate(answers)}
        final_summary = summary_template.format(**answer_dict)

        await update.message.reply_text(final_summary + disclaimer, parse_mode=ParseMode.MARKDOWN)

        context.user_data.clear()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The main message handler. Routes to conversation or new query."""
    if not update.message or not update.message.text:
        return

    user_message = update.message.text

    if 'symptom_flow' in context.user_data:
        await handle_symptom_conversation(update, context)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    language, disclaimer = _get_language_details(user_message)
    triage_result = triage_user_input(user_message, language)
    if triage_result:
        await update.message.reply_text(triage_result, parse_mode=ParseMode.MARKDOWN)
        return

    intent_prompt = INTENT_PROMPT_TEMPLATE.format(language=language, query=user_message)
    intent_response_text = run_ai_prompt(intent_prompt)
    intent, drug_name, symptom = _parse_intent(intent_response_text)
    logger.info(f"Intent: {intent}, Drug: {drug_name}, Symptom: {symptom}")

    # Path 1: Start an interactive symptom funnel if the symptom is in the detailed list
    if intent == "B" and symptom in SYMPTOM_QUESTIONS:
        logger.info(f"Starting symptom funnel for '{symptom}'")
        context.user_data['language'] = language
        context.user_data['disclaimer'] = disclaimer
        context.user_data['symptom_flow'] = symptom
        context.user_data['question_index'] = 0
        context.user_data['answers'] = []

        first_question = SYMPTOM_QUESTIONS[symptom]['questions'][0]
        await update.message.reply_text(first_question)

    # Path 2: Provide a pre-canned response if the symptom is in the simple minor diseases list
    elif intent == "B" and symptom in MINOR_DISEASES:
        logger.info(f"Providing pre-canned info for minor disease: '{symptom}'")
        response_text = MINOR_DISEASES[symptom]
        await update.message.reply_text(response_text + disclaimer, parse_mode=ParseMode.MARKDOWN)

    # Path 3: Fallback for drugs, multiple symptoms, or completely unknown topics
    else:
        logger.info("Using general AI fallback for query.")
        fallback_prompt = f"Please provide a brief, helpful, and safe response in {language} for the health-related query: '{user_message}'. Do not prescribe medication."
        response_text = run_ai_prompt(fallback_prompt)
        await update.message.reply_text(response_text + disclaimer, parse_mode=ParseMode.MARKDOWN)

# =================================================================================
# 6. MAIN EXECUTION
# =================================================================================
# ... [Unchanged section] ...
def main() -> None:
    if not BOT_TOKEN:
        logger.critical("Telegram BOT_TOKEN not found. Please add it to your .env file or environment.")
        return

    logger.info("Starting ENHANCED NLP health bot with Triage System...")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running. Press Ctrl-C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()