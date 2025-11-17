# -*- coding: utf-8 -*-
"""
A multi-lingual Telegram health bot that uses OpenRouter.ai for intent classification 
and response generation, and provides information from the OpenFDA database.
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

# --- Model & API Constants ---
FDA_API_URL = "https://api.fda.gov/drug/label.json"
# FIX: Define the model you want to use via OpenRouter
OPENROUTER_MODEL_NAME = "openai/gpt-3.5-turbo" 

# --- In-Memory Cache ---
QUERY_CACHE: Dict[str, str] = {}

# --- Language Mappings ---
LANGUAGE_MAP = {
    'en': 'English', 'hi': 'Hindi', 'bn': 'Bengali', 'te': 'Telugu',
    'mr': 'Marathi', 'ta': 'Tamil', 'gu': 'Gujarati', 'kn': 'Kannada',
    'or': 'Odia', 'ml': 'Malayalam', 'pa': 'Punjabi'
}

# --- Translated Disclaimers ---
DISCLAIMER_MAP = {
    'English': "\n\n---\n*⚠️ IMPORTANT: I am an AI assistant, not a doctor. This information is for educational purposes only. You MUST consult a qualified healthcare professional for any medical concerns or before taking any medication.*",
    'Hindi': "\n\n---\n*⚠️ महत्वपूर्ण: मैं एक एआई सहायक हूं, डॉक्टर नहीं। यह जानकारी केवल शैक्षिक उद्देश्यों के लिए है। किसी भी चिकित्सीय चिंता के लिए या कोई भी दवा लेने से पहले आपको एक योग्य स्वास्थ्य देखभाल पेशेवर से परामर्श करना चाहिए।*",
    'Bengali': "\n\n---\n*⚠️ গুরুত্বপূর্ণ: আমি একজন এআই সহকারী, ডাক্তার নই। এই তথ্য শুধুমাত্র শিক্ষামূলক উদ্দেশ্যে। যেকোনো চিকিৎসার জন্য অথবা কোনো ঔষধ খাওয়ার আগে আপনাকে অবশ্যই একজন যোগ্য স্বাস্থ্য বিশেষজ্ঞের সাথে পরামর্শ করতে হবে।*",
    'Telugu': "\n\n---\n*⚠️ ముఖ్యం: నేను ఒక ఏఐ అసిస్టెంట్‌ను, డాక్టర్‌ను కాదు। ఈ సమాచారం విద్యా ప్రయోజనాల కోసం మాత్రమే। ఏదైనా వైద్య సమస్యల కోసం లేదా ఏదైనా మందు తీసుకునే ముందు మీరు తప్పనిసరిగా ఒక అర్హత కలిగిన ఆరోగ్య నిపుణుడిని సంప్రదించాలి।*",
    'Marathi': "\n\n---\n*⚠️ महत्त्वाचे: मी एक एआय सहाय्यक आहे, डॉक्टर नाही। ही माहिती केवळ शैक्षणिक हेతूंसाठी आहे। कोणत्याही वैद्यकीय चिंतेसाठी किंवा कोणतेही औषध घेण्यापूर्वी तुम्ही पात्र आरोग्यसेवा व्यावसायिकांचा सल्ला घ्यावा।*",
    'Tamil': "\n\n---\n*⚠️ முக்கியம்: நான் ஒரு ஏஐ உதவியாளர், மருத்துவர் அல்ல। இந்தத் தகவல் கல்வி நோக்கங்களுக்காக மட்டுமே। எந்தவொரு மருத்துவ கவலைகளுக்கும் அல்லது எந்த மருந்தையும் எடுத்துக்கொள்வதற்கு முன்பு நீங்கள் ஒரு தகுதிவாய்ந்த சுகாதார நிபுணரை அணுக வேண்டும்।*",
    'Gujarati': "\n\n---\n*⚠️ મહત્વપૂર્ણ: હું એક એઆઈ સહાયક છું, ડૉક્ટર નથી। આ માહિતી ફક્ત શૈક્ષણિક હેતુઓ માટે છે। કોઈપણ તબીબી ચિંતાઓ માટે અથવા કોઈપણ દવા લેતા પહેલા તમારે યોગ્ય આરોગ્યસંભાળ વ્યવસાયીની સલાહ લેવી જ જોઇએ।*",
    'Kannada': "\n\n---\n*⚠️ ಪ್ರಮುಖ: ನಾನು ಎಐ ಸಹಾಯಕ, ವೈದ್ಯನಲ್ಲ। ಈ ಮಾಹಿತಿಯು ಶೈಕ್ಷಣಿಕ ಉದ್ದೇಶಗಳಿಗಾಗಿ ಮಾತ್ರ। ಯಾವುದೇ ವೈದ್ಯಕೀಯ ಕಾಳಜಿಗಳಿಗಾಗಿ ಅಥವಾ ಯಾವುದೇ ಔಷಧಿಯನ್ನು ತೆಗೆದುಕೊಳ್ಳುವ ಮೊದಲು ನೀವು ಅರ್ಹ ಆರೋಗ್ಯ ವೃತ್ತಿಪರರನ್ನು ಸಂಪರ್ಕಿಸಬೇಕು।*",
    'Odia': "\n\n---\n*⚠️ ଗୁରୁତ୍ୱପୂର୍ଣ୍ଣ: ମୁଁ ଜଣେ AI ସହାୟକ, ଡାକ୍ତର ନୁହେଁ। ଏହି ସୂଚନା କେବଳ ଶିକ୍ଷାଗତ ଉଦ୍ଦେଶ୍ୟ ପାଇଁ। କୌଣସି ଚିକିତ୍ସା ସମ୍ବନ୍ଧୀୟ ଚିନ୍ତା ପାଇଁ କିମ୍ବା କୌଣସି ଔଷଧ ସେବନ କରିବା ପୂର୍ବରୁ ଆପଣ ନିଶ୍ଚିତ ଭାବରେ ଜଣେ ଯୋଗ୍ୟ ସ୍ୱାସ୍ଥ୍ୟସେବା ବୃତ୍ତିଗତଙ୍କ ସହିତ ପରାମର୍ଶ କରନ୍ତୁ।*",
    'Malayalam': "\n\n---\n*⚠️ പ്രധാനം: ഞാൻ ഒരു എഐ അസിസ്റ്റൻ്റാണ്, ഡോക്ടറല്ല. ഈ വിവരം വിദ്യാഭ്യാസ ആവശ്യങ്ങൾക്ക് മാത്രമുള്ളതാണ്. ഏതെങ്കിലും വൈദ്യപരമായ ആശങ്കകൾക്ക് അല്ലെങ്കിൽ ഏതെങ്കിലും മരുന്ന് കഴിക്കുന്നതിന് മുമ്പ് നിങ്ങൾ ഒരു യോഗ്യതയുള്ള ആരോഗ്യ വിദഗ്ദ്ധനെ സമീപിക്കേണ്ടതാണ്.*",
    'Punjabi': "\n\n---\n*⚠️ ਜ਼ਰੂਰੀ: ਮੈਂ ਇੱਕ ਏਆਈ ਸਹਾਇਕ ਹਾਂ, ਡਾਕਟਰ ਨਹੀਂ। ਇਹ ਜਾਣਕਾਰੀ ਸਿਰਫ਼ ਵਿਦਿਅਕ ਉਦੇਸ਼ਾਂ ਲਈ ਹੈ। ਕਿਸੇ ਵੀ ਡਾਕਟਰੀ ਚਿੰਤਾਵਾਂ ਲਈ ਜਾਂ ਕੋਈ ਵੀ ਦਵਾਈ ਲੈਣ ਤੋਂ ਪਹਿਲਾਂ ਤੁਹਾਨੂੰ ਇੱਕ ਯੋਗ ਸਿਹਤ ਸੰਭਾਲ ਪੇਸ਼ੇਵਰ ਨਾਲ ਸਲਾਹ-ਮਸ਼ਵਰਾ ਕਰਨਾ ਚਾਹੀਦਾ ਹੈ।*"
}

# --- Prompt Templates ---
INTENT_PROMPT_TEMPLATE = """
Analyze the user's query which is in {language}: "{query}"
What is the user's primary intent? Choose one:
A) Asking for information about a specific DRUG.
B) Asking a general question about a single SYMPTOM or CONDITION.
C) Listing multiple SYMPTOMS to understand potential related health topics.

If the intent is (A), also extract the drug name in ENGLISH.

Respond in this exact format:
Intent: [A, B, or C]
Drug Name: [drug name in ENGLISH or "N/A"]
"""

DRUG_SYNTHESIS_PROMPT = """
Strict command: You MUST write the entire response in {language}.
The user asked about '{drug_name}'. Here is the factual data: {fda_data}.
Please present this information to the user in a helpful and clear way in {language}.
"""

SINGLE_SYMPTOM_PROMPT = """
Strict command: You MUST write the entire response in {language}.
A user is asking about "{query}".
Please provide a brief, encyclopedia-style summary of this topic. Then, add a section called "General Advice" (translate "General Advice" into {language}).
In this section, provide 2-3 general wellness tips. Do NOT suggest any specific medications.
"""

MULTIPLE_SYMPTOMS_PROMPT = """
Strict command: You MUST write the entire response in {language}.
A user is describing these symptoms: "{query}".
Your task is to act as a Symptom Information Navigator. DO NOT DIAGNOSE.
1.  Identify and list up to three common, non-emergency conditions that are sometimes associated with these symptoms.
2.  For each condition, write a very brief, one-sentence, neutral description.
3.  Conclude with a strong statement that the user MUST see a doctor for a proper diagnosis.
"""

TRANSLATE_FALLBACK_PROMPT = """
Translate this sentence into {language}: {text}
"""

# =================================================================================
# 2. SETUP AND INITIALIZATION
# =================================================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Load Environment Variables ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- Configure OpenRouter Client ---
# FIX: Removed hardcoded API key and configured the client correctly.
# This client will be used for all AI calls.
if not OPENROUTER_API_KEY:
    logger.critical("OPENROUTER_API_KEY not found in environment variables. Bot cannot start.")
    exit()

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)
logger.info("OpenRouter client configured successfully.")


# FIX: Removed the incorrect 'genai' (Google) configuration and the unused BioBERT model loading
# to improve startup time and prevent errors.

# =================================================================================
# 3. API AND HELPER FUNCTIONS
# =================================================================================

def fetch_drug_info(query: str) -> Optional[str]:
    """Fetches drug information from the OpenFDA API."""
    logger.info(f"Fetching FDA info for drug: {query}")
    params = {"search": f'(openfda.brand_name:"{query}" OR openfda.generic_name:"{query}")', "limit": 1}
    
    try:
        response = requests.get(FDA_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "results" not in data or not data["results"]:
            return None
        
        item = data["results"][0]
        official_name_list = item.get("openfda", {}).get("generic_name", [query.capitalize()])
        official_name = official_name_list[0] if official_name_list else query.capitalize()
        purpose_list = item.get("purpose", ["No purpose information available."])
        purpose = purpose_list[0] if purpose_list else "No purpose information available."
        
        return f"**{official_name.capitalize()}** is typically used for: {purpose}"

    except requests.RequestException as e:
        logger.error(f"Error fetching from OpenFDA for '{query}': {e}")
        return None

# FIX: Rewritten to use the correctly configured OpenRouter client.
def run_ai_prompt(prompt_text: str) -> str:
    """Sends a prompt to the OpenRouter API and returns the text response."""
    try:
        logger.info(f"Sending prompt to OpenRouter: '{prompt_text[:100].replace('\n', ' ')}...'")
        
        completion = client.chat.completions.create(
          model=OPENROUTER_MODEL_NAME,
          messages=[
            {
              "role": "user",
              "content": prompt_text,
            },
          ],
        )
        
        if completion.choices:
            return completion.choices[0].message.content
        else:
            logger.error("API call to OpenRouter returned no choices.")
            return "Sorry, the AI returned an empty response."

    except Exception as e:
        logger.error(f"OpenRouter API call failed: {e}")
        return "Sorry, I am having trouble connecting to my AI brain right now."

# =================================================================================
# 4. CORE LOGIC FOR HANDLING QUERIES
# =================================================================================

def _get_language_details(query: str) -> Tuple[str, str]:
    """Detects language from query and returns the language name and its disclaimer."""
    try:
        lang_code = detect(query)
        language = LANGUAGE_MAP.get(lang_code, 'English')
    except LangDetectException:
        language = 'English'
    
    disclaimer = DISCLAIMER_MAP.get(language, DISCLAIMER_MAP['English'])
    logger.info(f"Detected language: {language}")
    return language, disclaimer

def _parse_intent(response_text: str) -> Tuple[str, str]:
    """Parses the intent and drug name from the AI's classification response."""
    intent = "C" # Default to most cautious intent
    drug_name = "N/A"
    
    lines = response_text.strip().split('\n')
    for line in lines:
        if "Intent:" in line:
            if "A" in line: intent = "A"
            elif "B" in line: intent = "B"
        if "Drug Name:" in line:
            # Handle potential empty splits and strip whitespace/quotes
            parts = line.split("Drug Name:")
            if len(parts) > 1:
                drug_name = parts[1].strip().strip('"')
            
    return intent, drug_name

def _handle_drug_query(drug_name: str, language: str, disclaimer: str) -> str:
    """Handles logic for drug information queries (Path A)."""
    logger.info(f"Path A: Fetching FDA data for drug '{drug_name}'")
    fda_data = fetch_drug_info(drug_name.lower())
    
    if fda_data:
        prompt = DRUG_SYNTHESIS_PROMPT.format(language=language, drug_name=drug_name, fda_data=fda_data)
        return run_ai_prompt(prompt) + disclaimer
    else:
        fallback_text = f"I couldn't find specific information for '{drug_name}' in the FDA database."
        prompt = TRANSLATE_FALLBACK_PROMPT.format(language=language, text=fallback_text)
        return run_ai_prompt(prompt) + disclaimer

def get_bot_response(query: str) -> str:
    """
    Main function to process a user's query and generate a response.
    This orchestrates language detection, caching, intent classification, and response generation.
    """
    language, disclaimer = _get_language_details(query)
    normalized_query = f"{query.strip().lower()}_{language}"

    # --- Step 1: Check Cache ---
    if normalized_query in QUERY_CACHE:
        logger.info(f"Cache HIT for query: '{query}'.")
        return QUERY_CACHE[normalized_query]
    
    logger.info(f"Cache MISS. Starting new query for: '{query}'")

    # --- Step 2: Intent Classification ---
    intent_prompt = INTENT_PROMPT_TEMPLATE.format(language=language, query=query)
    intent_response_text = run_ai_prompt(intent_prompt)
    intent, drug_name = _parse_intent(intent_response_text)
    logger.info(f"Detected Intent: {intent}, Drug Name: {drug_name}")

    # --- Step 3: Route to appropriate logic path ---
    final_response = ""
    if intent == "A" and drug_name != "N/A" and drug_name:
        final_response = _handle_drug_query(drug_name, language, disclaimer)
    
    elif intent == "B":
        logger.info("Path B: Handling a single symptom query.")
        prompt = SINGLE_SYMPTOM_PROMPT.format(language=language, query=query)
        final_response = run_ai_prompt(prompt) + disclaimer
        
    else: # Default to Path C for multiple symptoms or unclear intent
        logger.info("Path C: Navigating multiple symptoms.")
        prompt = MULTIPLE_SYMPTOMS_PROMPT.format(language=language, query=query)
        final_response = run_ai_prompt(prompt) + disclaimer

    # --- Step 4: Cache and Return Response ---
    QUERY_CACHE[normalized_query] = final_response
    return final_response

# =================================================================================
# 5. TELEGRAM BOT HANDLERS
# =================================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user = update.effective_user
    welcome_text = (
        f"Hello {user.mention_html()}! नमस्ते! Welcome.\n\n"
        "I am a health information assistant. You can ask me about a drug (e.g., 'Tell me about Paracetamol'), "
        "a symptom (e.g., 'What is a fever?'), or list several symptoms (e.g., 'headache and nausea').\n\n"
        "Use /help to see more examples."
    )
    await update.message.reply_html(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends help information when the /help command is issued."""
    help_text = (
        "You can ask me questions in many Indian languages.\n\n"
        "Examples:\n"
        "- 'Tell me about lisinopril'\n"
        "- 'खांसी क्या है?' (What is a cough?)\n"
        "- 'തലവേദനയും പനിയും' (Headache and fever)\n\n"
        "<b>Important:</b> This bot is for informational purposes only and is not a substitute for professional medical advice."
    )
    await update.message.reply_html(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The main message handler. Processes non-command text messages."""
    if not update.message or not update.message.text:
        return
        
    user_message = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    
    response_text = get_bot_response(user_message)
    
    await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

# =================================================================================
# 6. MAIN EXECUTION
# =================================================================================

def main() -> None:
    """Starts the bot."""
    if not BOT_TOKEN:
        logger.critical("Telegram BOT_TOKEN not found. Please add it to your .env file or environment.")
        return

    logger.info("Starting ENHANCED NLP health bot...")
    
    # FIX: Removed hardcoded token and now uses the BOT_TOKEN from the environment.
    application = Application.builder().token(BOT_TOKEN).build()

    # --- Register Handlers ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running. Press Ctrl-C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()