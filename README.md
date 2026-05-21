# SwasthyaMitra - AI Health Assistant Bot

A multilingual Telegram health bot that provides symptom guidance, medication reminders, and nearby healthcare facility location services. Built for the Smart India Hackathon (SIH).

![Python](https://img.shields.io/badge/Python-3.11.9-blue)
![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue)
![Status](https://img.shields.io/badge/Status-Live-success)

## 🌟 Features

### 🤖 AI-Powered Health Assistance
- **Multi-language Support**: Supports English, Hindi, Bengali, Telugu, Marathi, Tamil, Gujarati, Kannada, Odia, Malayalam, and Punjabi
- **Intelligent Intent Classification**: Uses OpenRouter AI (GPT-3.5-turbo) to understand user queries
- **Symptom Triage**: Detects emergency symptoms and provides immediate guidance
- **Drug Information**: Fetches medication details from OpenFDA database

### 💊 Health Management
- **Symptom Logging**: Track symptoms with severity ratings (`/log`)
- **Health Summary**: View recent symptom history (`/summary`)
- **Medication Reminders**: Set daily reminders for medications (`/remind`)
- **Interactive Symptom Checker**: Guided questionnaire for common conditions

### 🏥 Location Services
- **Nearby Healthcare Finder**: Locate hospitals and pharmacies within 10km radius
- **Google Maps Integration**: Direct map links to healthcare facilities
- **Emergency Guidance**: First-aid instructions for critical symptoms

### 🔒 Safety Features
- **Medical Disclaimers**: Clear warnings that bot is not a substitute for professional advice
- **Emergency Detection**: Identifies life-threatening symptoms (chest pain, stroke, severe bleeding)
- **Reliable Sources**: Links to WHO and Mayo Clinic for health information

## 🚀 Live Demo

**Bot Username**: [@SwasthyaMitrabot](https://t.me/SwasthyaMitrabot)  
**Web Status**: [https://swasthyamitra-oop1.onrender.com](https://swasthyamitra-oop1.onrender.com)

> ⚠️ **Note**: Free tier sleeps after 15 minutes of inactivity. First message may take 30-60 seconds to wake up.

## 📋 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Start the bot and see welcome menu | `/start` |
| `/help` | Show available commands | `/help` |
| `/log` | Log a symptom with severity | `/log headache 7/10` |
| `/summary` | View recent symptom history | `/summary` |
| `/remind` | Set medication reminder | `/remind aspirin at 09:00` |
| `/locate` | Find nearby hospitals/pharmacies | `/locate` |

## 🛠️ Tech Stack

### Core Technologies
- **Python 3.11.9**: Main programming language
- **python-telegram-bot 21.3**: Telegram Bot API wrapper
- **Flask 3.0.3**: Web server for Render deployment
- **SQLite**: Local database for symptom logs and reminders

### AI & APIs
- **OpenAI SDK**: Interface for OpenRouter API
- **OpenRouter**: AI model routing (GPT-3.5-turbo)
- **OpenFDA API**: Drug information database
- **Google Maps Places API**: Healthcare facility search
- **langdetect**: Language detection

### Deployment
- **Render**: Cloud hosting platform
- **asyncio**: Asynchronous bot operations
- **threading**: Concurrent Flask + Bot execution

## 📦 Installation

### Prerequisites
- Python 3.11.9+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenRouter API Key (from [openrouter.ai](https://openrouter.ai))
- Google Maps API Key (optional, for location features)

### Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/Anuj-Gaud/swasthyaMitra.git
cd swasthyaMitra
```

2. **Create virtual environment**
```bash
python -m venv sih
# Windows
sih\Scripts\activate
# Linux/Mac
source sih/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the project root:
```env
BOT_TOKEN=your_telegram_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here  # Optional
WEBSITE_URL=https://your-website.com  # Optional
```

5. **Run the bot**
```bash
python main.py
```

## 🌐 Deployment on Render

### Step 1: Prepare Repository
Ensure these files exist:
- `requirements.txt` - Python dependencies
- `.python-version` - Python version (3.11.9)
- `runtime.txt` - Alternative Python version file

### Step 2: Create Web Service
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `swasthyamitra`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`

### Step 3: Set Environment Variables
Add these in Render's Environment section:
```
BOT_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
PYTHON_VERSION=3.11.9
```

### Step 4: Deploy
Click **Create Web Service** and wait 2-3 minutes for deployment.

## 📁 Project Structure

```
swasthyaMitra/
├── main.py                 # Entry point, Flask + Bot initialization
├── handlers.py             # Telegram command and message handlers
├── features.py             # AI logic, triage, location services
├── config.py               # Configuration, translations, prompts
├── database.py             # SQLite operations
├── jobs.py                 # Scheduled reminder jobs
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .python-version         # Python version specification
├── runtime.txt             # Alternative Python version file
└── README.md               # This file
```

## 🔧 Configuration

### Language Support
Add new languages in `config.py`:
```python
TRANSLATIONS = {
    'YourLanguage': {
        "REDIRECT_MESSAGE": "...",
        "SYMPTOM_QUESTIONS": {...},
        "MINOR_DISEASES": {...}
    }
}
```

### AI Model
Change the model in `config.py`:
```python
OPENROUTER_MODEL_NAME = "openai/gpt-4"  # or any OpenRouter model
```

### Emergency Symptoms
Customize in `config.py`:
```python
MAJOR_SYMPTOMS = ["chest pain", "difficulty breathing", ...]
```

## 🧪 Testing

### Test Locally
```bash
python main.py
```
Send `/start` to your bot on Telegram.

### Test Deployment
1. Check web endpoint: `https://your-app.onrender.com/health`
2. Should return: `{"status": "ok"}`
3. Test bot on Telegram

## 🐛 Troubleshooting

### Bot Not Responding
- Check `BOT_TOKEN` format: `123456789:ABC...XYZ` (must include colon)
- Verify token with @BotFather: `/mybots` → API Token
- Check Render logs for errors

### Python Version Issues
- Set `PYTHON_VERSION=3.11.9` in Render environment variables
- Python 3.14 has compatibility issues with python-telegram-bot

### Location Services Not Working
- Verify `GOOGLE_MAPS_API_KEY` is set
- Enable Places API in Google Cloud Console
- Check API quota limits

### Render Free Tier Sleep
- Service sleeps after 15 min inactivity
- First request takes 30-60 sec to wake
- Upgrade to paid tier for 24/7 uptime

## 📊 Database Schema

### Symptoms Table
```sql
CREATE TABLE symptoms (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    symptom TEXT NOT NULL,
    severity TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### Reminders Table
```sql
CREATE TABLE reminders (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    medication TEXT NOT NULL,
    time TEXT NOT NULL,
    job_name TEXT UNIQUE NOT NULL
)
```

## 🔐 Security Notes

- Never commit `.env` file to Git (already in `.gitignore`)
- Rotate API keys if accidentally exposed
- Use environment variables for all secrets
- Revoke compromised bot tokens via @BotFather

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is created for Smart India Hackathon (SIH). All rights reserved.

## 👥 Team

- **Developer**: Anuj Gaud
- **GitHub**: [@Anuj-Gaud](https://github.com/Anuj-Gaud)

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot framework
- [OpenRouter](https://openrouter.ai) - AI model routing
- [OpenFDA](https://open.fda.gov) - Drug information API
- [Render](https://render.com) - Cloud hosting platform

## 📞 Support

For issues or questions:
- Open an issue on [GitHub](https://github.com/Anuj-Gaud/swasthyaMitra/issues)
- Contact via Telegram: [@SwasthyaMitrabot](https://t.me/SwasthyaMitrabot)

---

**⚠️ Medical Disclaimer**: This bot is for informational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.
