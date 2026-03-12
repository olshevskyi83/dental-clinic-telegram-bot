import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "clinic.db")

ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {
    int(item.strip())
    for item in ADMIN_IDS_RAW.split(",")
    if item.strip().isdigit()
}

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env")