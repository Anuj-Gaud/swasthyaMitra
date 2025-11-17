# features.py
import logging
import requests
import config
import os
from typing import Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from openai import OpenAI
from config import OPENROUTER_MODEL_NAME, MAJOR_SYMPTOMS, MAJOR_DISEASE_GUIDANCE, TRANSLATIONS

logger = logging.getLogger(__name__)
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
print("GOOGLE_MAPS_API_KEY:", GOOGLE_MAPS_API_KEY)

def run_ai_prompt(prompt: str) -> str:
    try:
        response = client.chat.completions.create(model=OPENROUTER_MODEL_NAME, messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"AI prompt error: {e}")
        return "Language: English\nIntent: C\nDrug Name: N/A\nSymptom: N/A"

# features.py

def parse_ai_response(response_text: str) -> Tuple[str, str, str, str]:
    """
    Parses the AI's response, safely ignoring any lines that don't match the expected format.
    """
    language, intent, drug_name, symptom = "English", "C", "N/A", "N/A"
    data = {}

    # --- FIX: Added a check to ensure the line contains a colon before splitting ---
    for line in response_text.strip().split('\n'):
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                data[key] = value

    language = data.get("Language", "English")
    intent_char = data.get("Intent", "C")
    if "A" in intent_char: intent = "A"
    elif "B" in intent_char: intent = "B"
    else: intent = "C"

    drug_name = data.get("Drug Name", "N/A")
    symptom = data.get("Symptom", "N/A").lower()
    
    return language, intent, drug_name, symptom

def triage_user_input(user_message: str, language: str) -> Optional[Tuple[str, InlineKeyboardMarkup]]:
    """
    Checks for major symptoms. If found, returns a message AND an interactive button object.
    """
    normalized_message = user_message.lower()
    redirect_message = TRANSLATIONS.get(language, TRANSLATIONS['English'])["REDIRECT_MESSAGE"]
    
    for keyword in MAJOR_SYMPTOMS:
        if keyword in normalized_message:
            logger.warning(f"MAJOR SYMPTOM DETECTED: '{keyword}'.")
            
            # Create the button and keyboard markup
            keyboard = [[InlineKeyboardButton("🏥 Find a Nearby Hospital", callback_data="find_hospital")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            first_aid = ""
            for guidance_key, guidance_text in MAJOR_DISEASE_GUIDANCE.items():
                if guidance_key in normalized_message:
                    first_aid = guidance_text
                    break
            
            # --- FIX: Return the message and markup as two separate items ---
            if first_aid:
                message = f"<b>Immediate Guidance:</b> {first_aid}\n\n---\n\n{redirect_message}"
                return message, reply_markup # This is a tuple: (string, object)
            else:
                return redirect_message, reply_markup # This is also a tuple
            
    return None

# features.py

# ... (rest of your imports and code)

def find_nearby_health_services(lat: float, lon: float) -> Tuple[str, Optional[str]]:
    """
    Searches for hospitals and pharmacies, returning a formatted text list AND a Google Maps URL.
    """
    if not GOOGLE_MAPS_API_KEY:
        return "Location services are not configured by the administrator.", None
    
    # --- FIX: Generate a Google Maps URL that shows the search results on a map ---
    search_query = "hospitals and pharmacies"
    map_url = f"https://www.google.com/maps/search/?api=1&query={search_query.replace(' ', '+')}&location={lat},{lon}"

    search_types = "hospital|pharmacy"
    api_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius=10000&type={search_types}&key={GOOGLE_MAPS_API_KEY}"
    
    try:
        response = requests.get(api_url)
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return "Could not find any hospitals or medical stores within a 10km radius.", None
        
        message = "🏥 Here are some nearby health services:\n\n"
        for place in results[:5]: 
            name = place.get("name")
            address = place.get("vicinity")
            place_type = "Hospital" if "hospital" in place.get("types", []) else "Medical Store"
            emoji = "🏥" if place_type == "Hospital" else "💊"
            message += f"{emoji} <b>{name}</b> ({place_type})\n{address}\n\n"
            
        # Return both the text message and the map URL
        return message, map_url

    except Exception as e:
        logger.error(f"Google Maps API error: {e}")
        return "Sorry, I encountered an error trying to find nearby health services.", None


def translate_text(text: str, target_language: str, context: str = "general") -> str:
    """Uses the AI to translate text to a target language."""
    # We add context to get better translations (e.g., 'button' vs 'medical advice')
    prompt = f"Translate the following English text to {target_language}. The context is: {context}. Respond with only the translated text, nothing else.\n\nText: \"{text}\""
    try:
        response = run_ai_prompt(prompt)
        # Sometimes the AI includes quotes, so we remove them.
        return response.strip().strip('"')
    except Exception as e:
        logger.error(f"Translation failed for language {target_language}: {e}")
        return text # Fallback to English if translation fails    

# features.py

def get_language_pack(language: str) -> dict:
    """
    Finds a language pack in the config cache. If not found, it creates one
    by translating the English master template using the AI.
    """
    if language in config.TRANSLATIONS:
        # Cache Hit: Language already exists, return it instantly.
        return config.TRANSLATIONS[language]

    logger.info(f"Cache Miss: Creating new language pack for '{language}' on-demand.")
    
    # Cache Miss: Translate the English master pack.
    english_pack = config.TRANSLATIONS['English']
    new_pack = {
        "REDIRECT_MESSAGE": translate_text(english_pack["REDIRECT_MESSAGE"], language, "urgent medical redirect"),
        "SYMPTOM_QUESTIONS": {},
        "MINOR_DISEASES": {}
    }

    # Translate all the symptom funnels
    for symptom, data in english_pack["SYMPTOM_QUESTIONS"].items():
        translated_questions = [translate_text(q, language, "medical question") for q in data["questions"]]
        translated_summary = translate_text(data["final_summary"], language, "medical summary")
        new_pack["SYMPTOM_QUESTIONS"][symptom] = {
            "questions": translated_questions,
            "final_summary": translated_summary
        }

    # Translate all the minor disease info
    for disease, text in english_pack["MINOR_DISEASES"].items():
        new_pack["MINOR_DISEASES"][disease] = translate_text(text, language, "medical information")

    # Save the newly created pack to the cache for future use
    config.TRANSLATIONS[language] = new_pack
    logger.info(f"Successfully created and cached new language pack for '{language}'.")
    
    return new_pack    