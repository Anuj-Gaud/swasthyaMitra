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

# =================================================================================
# 1. CONSTANTS AND CONFIGURATION
# =================================================================================

FDA_API_URL = "https://api.fda.gov/drug/label.json"
OPENROUTER_MODEL_NAME = "openai/gpt-3.5-turbo"
# IMPORTANT: This must be a permanent, public URL from a deployed website.
WEBSITE_URL = "https://health-ai-assistant-a1af8fd6.base44.app"

# --- Enhanced Triage System Constants ---
MAJOR_SYMPTOMS = [
    "chest pain", "crushing pain", "tightness in chest", "chest pressure",
    "pain radiating", "pain in arm or jaw", "pain in shoulder",
    "can't breathe", "difficulty breathing", "shortness of breath", "gasping for air",
    "choking", "wheezing", "bluish lips", "blue skin", "cyanosis",
    "sudden numbness", "weakness in limb", "face drooping", "one side weak",
    "sudden confusion", "disoriented", "trouble speaking", "slurred speech",
    "severe headache", "worst headache of my life", "thunderclap headache",
    "seizure", "convulsion", "loss of consciousness", "fainting",
    "sudden vision loss", "double vision", "loss of balance", "trouble walking",
    "head injury with confusion", "head injury with vomiting",
    "severe bleeding", "uncontrolled bleeding", "bleeding that won't stop",
    "severe abdominal pain", "unbearable stomach pain", "rigid belly",
    "vomiting blood", "coffee ground vomit",
    "black stool", "tarry stool", "maroon stool", "blood in stool",
    "major injury", "car accident", "fall from height",
    "severe burn", "large burn", "chemical burn", "electrical burn",
    "broken bone", "bone sticking out", "obvious deformity",
    "allergic reaction", "swollen tongue", "difficulty swallowing", "hives all over",
    "throat closing", "rapidly spreading rash", "hoarse voice after sting",
    "suicidal", "want to harm myself", "end my life",
    "overdose", "took too many pills",
    "high fever with stiff neck",
    "sudden testicular pain",
    "bleeding while pregnant",
]

# --- Major Disease First-Aid Guidance ---
MAJOR_DISEASE_GUIDANCE = {
    "chest pain": "⚠️ For any chest pain, it's safest to stop all activity and rest. Loosen any tight clothing.",
    "breathing": "⚠️ If you have difficulty breathing, try to stay calm and sit upright.",
    "bleeding": "🚨 For severe bleeding, apply firm, direct pressure to the wound with a clean cloth.",
    "stroke": "⚠️ For stroke symptoms (numbness, face drooping), note the time they first appeared.",
    "seizure": "⚠️ If someone is having a seizure, guide them to the floor and turn them onto their side.",
    "burn": "⚠️ For a severe burn, run cool (not cold) water over the area for 10-20 minutes.",
    "allergic reaction": "⚠️ For a severe allergic reaction, use an epinephrine auto-injector if available and call for help.",
    "suicidal": "❤️ If you are having thoughts of harming yourself, please talk to someone right away.",
    "head injury": "⚠️ For a head injury with confusion, keep the person still and awake.",
    "choking": "🚨 For choking, encourage them to cough forcefully. If they cannot, perform the Heimlich maneuver."
}

# --- Multilingual Text Structure (Add more languages here) ---
TRANSLATIONS = {
    'English': {
        "REDIRECT_MESSAGE": (
            f"Based on your symptoms, it's crucial to consult a medical professional immediately. "
            f"My capabilities are limited, and I cannot provide a medical diagnosis.\n\n"
            f"<b>Please find resources on our <a href='{WEBSITE_URL}'>official health portal</a>.</b>\n\n"
            f"<i>If this is a medical emergency, please call your local emergency services immediately.</i>"
        ),
        "SYMPTOM_QUESTIONS": {
            "headache": { "questions": ["To be safe, are you experiencing the worst headache of your life, sudden onset, fever, or weakness? (yes/no)", "How would you describe the pain? (e.g., dull ache or sharp, throbbing pain)", "Are you sensitive to light or sound?"], "final_summary": "Based on your description (pain: {ans2}, sensitivity: {ans3}), general advice for headaches includes rest and hydration. For persistent or severe pain, please see a doctor." },
            "cough": { "questions": ["To be safe, are you also having significant chest pain or difficulty breathing? (yes/no)", "Is the cough 'dry' or 'wet' (with mucus)?", "Do you also have a sore throat?"], "final_summary": "For a {ans2} cough, staying hydrated with warm liquids can help soothe irritation. A pharmacist can advise on OTC options. If symptoms persist, see a doctor." },
        },
        "MINOR_DISEASES": {
            "common cold": "The common cold is a viral infection. General advice includes rest, hydration, and using over-the-counter remedies.",
            "acne": "Acne is a common skin condition. Keeping your skin clean and using over-the-counter products can be effective.",
        }
    },
    'Hindi': {
        "REDIRECT_MESSAGE": (
            f"आपके लक्षणों के आधार पर, तुरंत एक चिकित्सा पेशेवर से परामर्श करना महत्वपूर्ण है। "
            f"मेरी क्षमताएं सीमित हैं, और मैं चिकित्सा निदान प्रदान नहीं कर सकता।\n\n"
            f"<b>कृपया हमारे <a href='{WEBSITE_URL}'>आधिकारिक स्वास्थ्य पोर्टल</a> पर संसाधन खोजें।</b>\n\n"
            f"<i>यदि यह एक चिकित्सा आपातकाल है, तो कृपया तुरंत अपनी स्थानीय आपातकालीन सेवाओं को कॉल करें।</i>"
        ),
        "SYMPTOM_QUESTIONS": {
            "headache": { "questions": ["सुरक्षा के लिए, क्या आप अपने जीवन के सबसे बुरे सिरदर्द, अचानक शुरुआत, बुखार, या कमजोरी का अनुभव कर रहे हैं? (हाँ/नहीं)", "आप दर्द का वर्णन कैसे करेंगे? (जैसे, हल्का दर्द या तेज, धड़कता हुआ दर्द)", "क्या आप प्रकाश या ध्वनि के प्रति संवेदनशील हैं?"], "final_summary": "आपके विवरण (दर्द: {ans2}, संवेदनशीलता: {ans3}) के आधार पर, सिरदर्द के लिए सामान्य सलाह में आराम और हाइड्रेशन शामिल है। लगातार या गंभीर दर्द के लिए, कृपया डॉक्टर देखें।" },
            "cough": { "questions": ["सुरक्षा के लिए, क्या आपको सीने में तेज दर्द या सांस लेने में कठिनाई हो रही है? (हाँ/नहीं)", "क्या खांसी 'सूखी' है या 'गीली' (बलगम के साथ)?", "क्या आपके गले में भी खराश है?"], "final_summary": "{ans2} खांसी के लिए, गर्म तरल पदार्थों से हाइड्रेटेड रहने से जलन को शांत करने में मदद मिल सकती है। एक फार्मासिस्ट OTC विकल्पों पर सलाह दे सकता है। यदि लक्षण बने रहते हैं, तो डॉक्टर से मिलें।" },
        },
        "MINOR_DISEASES": {
            "common cold": "सामान्य सर्दी एक वायरल संक्रमण है। सामान्य सलाह में आराम, हाइड्रेशन और ओवर-द-काउंटर उपचारों का उपयोग करना शामिल है।",
            "acne": "मुंहासे एक आम त्वचा की स्थिति है। अपनी त्वचा को साफ रखना और ओवर-द-काउंटर उत्पादों का उपयोग करना प्रभावी हो सकता है।",
        }
    }
}

DISCLAIMER_MAP = {
    'English': "\n\n---\n*⚠️ IMPORTANT: I am an AI assistant, not a doctor...",
    'Hindi': "\n\n---\n*⚠️ महत्वपूर्ण: मैं एक एआई सहायक हूं, डॉक्टर नहीं...",
}

# --- AI Prompt Template ---
### IMPROVED ###
INTENT_PROMPT_TEMPLATE = """
Analyze the user's query: "{query}"

Perform the following tasks:
1.  **Detect Language:** Identify the primary language of the query from this list: {supported_languages}.
2.  **Classify Intent:** Determine the user's primary intent. Choose one: [A, B, C].
    A) Asking for information about a specific DRUG.
    B) Asking a general question about a single SYMPTOM or CONDITION.
    C) Listing multiple SYMPTOMS.
3.  **Extract Entities:**
    - If Intent is (A), extract the drug name in ENGLISH.
    - If Intent is (B), extract the single symptom in ENGLISH (e.g., 'headache', 'cough').

Respond in this exact format, with each item on a new line:
Language: [Detected Language, e.g., Hindi]
Intent: [A, B, or C]
Drug Name: [drug name in ENGLISH or "N/A"]
Symptom: [symptom in ENGLISH or "N/A"]
"""

# =================================================================================
# 2. SETUP AND INITIALIZATION
# =================================================================================
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not (BOT_TOKEN and OPENROUTER_API_KEY):
    logger.critical("BOT_TOKEN or OPENROUTER_API_KEY not found in environment variables.")
    exit()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# =================================================================================
# 3. API AND HELPER FUNCTIONS
# =================================================================================
def run_ai_prompt(prompt: str) -> str:
    try:
        response = client.chat.completions.create(model=OPENROUTER_MODEL_NAME, messages=[{"role": "user", "content": prompt}], max_tokens=150, temperature=0.2)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error in run_ai_prompt: {e}")
        return "Language: English\nIntent: C\nDrug Name: N/A\nSymptom: N/A"

# =================================================================================
# 4. CORE LOGIC FOR HANDLING QUERIES
# =================================================================================
### IMPROVED ###
def triage_user_input(user_message: str, language: str) -> Optional[str]:
    normalized_message = user_message.lower()
    lang_pack = TRANSLATIONS.get(language, TRANSLATIONS['English'])
    redirect_message = lang_pack["REDIRECT_MESSAGE"]
    guidance_dict = lang_pack.get("MAJOR_DISEASE_GUIDANCE", {})
    guidance_map = { "chest pain": ["chest", "radiating", "jaw", "shoulder"], "breathing": ["breath", "gasping", "wheezing", "bluish", "cyanosis"], "choking": ["choking"], "bleeding": ["bleeding"], "stroke": ["numbness", "weakness", "drooping", "confusion", "disoriented", "speech"], "seizure": ["seizure", "convulsion"], "head injury": ["head injury"], "burn": ["burn"], "allergic reaction": ["allergic", "swollen", "hives", "throat closing"], "suicidal": ["suicidal", "harm myself", "end my life", "overdose"] }

    for keyword in MAJOR_SYMPTOMS:
        if keyword in normalized_message:
            logger.warning(f"MAJOR SYMPTOM DETECTED: '{keyword}'.")
            first_aid = ""
            for guidance_key, triggers in guidance_map.items():
                if any(trigger in keyword for trigger in triggers):
                    first_aid = guidance_dict.get(guidance_key, "")
                    break
            if first_aid:
                return f"{first_aid}\n\n---\n\n{redirect_message}"
            else:
                return redirect_message
    return None

### IMPROVED ###
def _parse_ai_response(response_text: str) -> Tuple[str, str, str, str]:
    language, intent, drug_name, symptom = "English", "C", "N/A", "N/A"
    lines = response_text.strip().split('\n')
    for line in lines:
        if "Language:" in line and len(line.split("Language:")) > 1:
            language = line.split("Language:")[1].strip()
        elif "Intent:" in line:
            if "A" in line: intent = "A"
            elif "B" in line: intent = "B"
        elif "Drug Name:" in line and len(line.split("Drug Name:")) > 1:
            drug_name = line.split("Drug Name:")[1].strip().strip('"')
        elif "Symptom:" in line and len(line.split("Symptom:")) > 1:
            symptom_text = line.split("Symptom:")[1].strip().lower().strip()
            if "stomach" in symptom_text or "belly" in symptom_text: symptom = "stomach pain"
            elif "athlete" in symptom_text: symptom = "athletes foot"
            else: symptom = symptom_text
    return language, intent, drug_name, symptom

# =================================================================================
# 5. TELEGRAM BOT HANDLERS
# =================================================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 Welcome to the Health Bot! Type your question to get started.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("ℹ️ *Help*\n\nYou can ask questions like:\n- What are the side effects of paracetamol?\n- I have a headache, what should I do?", parse_mode=ParseMode.MARKDOWN)
    
async def handle_symptom_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    state = context.user_data
    symptom_flow, question_index, answers, language = state['symptom_flow'], state['question_index'], state['answers'], state['language']
    lang_pack = TRANSLATIONS.get(language, TRANSLATIONS['English'])
    answers.append(user_message)
    
    if question_index == 0 and ('yes' in user_message.lower() or 'हाँ' in user_message):
        logger.warning(f"User answered YES to triage question for '{symptom_flow}'. Redirecting.")
        ### FIXED ###
        await update.message.reply_text(lang_pack["REDIRECT_MESSAGE"], parse_mode=ParseMode.HTML)
        context.user_data.clear()
        return

    symptom_questions = lang_pack.get("SYMPTOM_QUESTIONS", {})
    current_question_list = symptom_questions.get(symptom_flow, {}).get("questions", [])
    
    if (question_index + 1) < len(current_question_list):
        state['question_index'] += 1
        await update.message.reply_text(current_question_list[state['question_index']])
    else:
        summary_template = symptom_questions.get(symptom_flow, {}).get("final_summary", "Processing complete.")
        answer_dict = {f'ans{i+1}': ans for i, ans in enumerate(answers)}
        final_summary = summary_template.format(**answer_dict)
        await update.message.reply_text(final_summary + DISCLAIMER_MAP.get(language, DISCLAIMER_MAP['English']), parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text: return
    user_message = update.message.text

    if 'symptom_flow' in context.user_data:
        await handle_symptom_conversation(update, context)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    supported_languages = ", ".join(TRANSLATIONS.keys())
    prompt = INTENT_PROMPT_TEMPLATE.format(query=user_message, supported_languages=supported_languages)
    ai_response = run_ai_prompt(prompt)
    language, intent, drug_name, symptom = _parse_ai_response(ai_response)
    
    logger.info(f"AI Detected: Language={language}, Intent={intent}, Drug={drug_name}, Symptom={symptom}")
    
    triage_result = triage_user_input(user_message, language)
    if triage_result:
        ### FIXED ###
        await update.message.reply_text(triage_result, parse_mode=ParseMode.HTML)
        return
        
    lang_pack = TRANSLATIONS.get(language, TRANSLATIONS['English'])
    symptom_questions = lang_pack.get("SYMPTOM_QUESTIONS", {})
    minor_diseases = lang_pack.get("MINOR_DISEASES", {})
    disclaimer = DISCLAIMER_MAP.get(language, DISCLAIMER_MAP['English'])

    if intent == "B" and symptom in symptom_questions:
        logger.info(f"Starting symptom funnel for '{symptom}' in {language}")
        context.user_data.update({'language': language, 'symptom_flow': symptom, 'question_index': 0, 'answers': []})
        await update.message.reply_text(symptom_questions[symptom]['questions'][0])
    
    elif intent == "B" and symptom in minor_diseases:
        logger.info(f"Providing pre-canned info for '{symptom}' in {language}")
        await update.message.reply_text(minor_diseases[symptom] + disclaimer, parse_mode=ParseMode.MARKDOWN)
        
    else:
        logger.info(f"Using general AI fallback for query in {language}.")
        fallback_prompt = f"Please provide a brief, helpful, and safe response in {language} for the health query: '{user_message}'. Do not prescribe medication."
        await update.message.reply_text(run_ai_prompt(fallback_prompt) + disclaimer, parse_mode=ParseMode.MARKDOWN)

# =================================================================================
# 6. MAIN EXECUTION
# =================================================================================
def main() -> None:
    if not BOT_TOKEN:
        logger.critical("Telegram BOT_TOKEN not found. Please check your .env file.")
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