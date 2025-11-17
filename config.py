# config.py
WEBSITE_URL = "https://health-ai-assistant-a1af8fd6.base44.app"
OPENROUTER_MODEL_NAME = "openai/gpt-3.5-turbo"
WEBSITE_LINK_HTML = f"\n\n<b>For more resources, visit our <a href='{WEBSITE_URL}'>official health portal</a>.</b>"

MAJOR_SYMPTOMS = ["chest pain", "crushing pain", "tightness in chest", "can't breathe", "difficulty breathing", "shortness of breath", "sudden numbness", "face drooping", "sudden confusion", "severe headache", "seizure", "uncontrolled bleeding", "severe burn", "swollen tongue", "suicidal", "overdose", "high fever with stiff neck"]
MAJOR_DISEASE_GUIDANCE = {
    "chest pain": "⚠️ For any chest pain, it's safest to stop all activity and rest. Loosen any tight clothing.",
    "breathing": "⚠️ If you have difficulty breathing, try to stay calm and sit upright.",
    "bleeding": "🚨 For severe bleeding, apply firm, direct pressure to the wound with a clean cloth.",
    "stroke": "⚠️ For stroke symptoms (numbness, face drooping), note the time they first appeared.",
    "seizure": "⚠️ If someone is having a seizure, guide them to the floor and turn them onto their side.",
    "burn": "⚠️ For a severe burn, run cool (not cold) water over the area for 10-20 minutes.",
    "allergic reaction": "⚠️ For a severe allergic reaction, use an epinephrine auto-injector if available and call for help.",
    "suicidal": "❤️ If you are having thoughts of harming yourself, please talk to someone right away."
}

TRANSLATIONS = {
    'English': {
        "REDIRECT_MESSAGE": (f"Based on your symptoms, it's crucial to consult a medical professional immediately. My capabilities are limited.\n\n<b>Please find resources on our <a href='{WEBSITE_URL}'>official health portal</a>.</b>\n\n<i>If this is a medical emergency, call your local emergency services.</i>"),
        "SYMPTOM_QUESTIONS": {"headache": {"questions": ["To be safe, are you experiencing the worst headache of your life, a sudden onset, or weakness? (yes/no)", "Describe the pain (e.g., dull ache or sharp throbbing)?", "Are you sensitive to light?"], "final_summary": "For headaches like yours (pain: {ans2}, sensitivity: {ans3}), rest and hydration are advised. For severe pain, see a doctor."},},
        "MINOR_DISEASES": {"common cold": "The common cold is a viral infection. General advice includes rest and hydration.", "acne": "Acne is a common skin condition. Keep your skin clean and use OTC products."},
    },
}

RELIABLE_SOURCES = { "common cold": "https://www.who.int/news-room/fact-sheets/detail/common-cold", "headache": "https://www.mayoclinic.org/symptoms/headache/basics/definition/sym-20050800",}
DISCLAIMER_MAP = {'English': "\n\n---\n*⚠️ IMPORTANT: I am an AI assistant, not a doctor...*"}
INTENT_PROMPT_TEMPLATE = """You are 'CareBot', a friendly and empathetic health assistant. Your tone should be reassuring and professional. Never give a diagnosis. Analyze the user's query: "{query}"
1. Detect Language: Identify from this list: {supported_languages}.
2. Classify Intent: Choose one: [A, B, C]. A) DRUG, B) single SYMPTOM, C) multiple SYMPTOMS.
3. Extract Entities: If (A), extract drug name. If (B), extract symptom.
Respond in this exact format:
Language: [Detected Language]
Intent: [A, B, or C]
Drug Name: [drug name or "N/A"]
Symptom: [symptom or "N/A"]
"""