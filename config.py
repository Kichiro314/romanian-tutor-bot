import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Bucharest")
MORNING_LESSON_HOUR = int(os.getenv("MORNING_LESSON_HOUR", "9"))
EVENING_QUIZ_HOUR = int(os.getenv("EVENING_QUIZ_HOUR", "19"))

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY is not set in .env")
