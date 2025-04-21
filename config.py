import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET_CODE = os.getenv("SECRET_CODE")
API_URL = os.getenv("API_URL")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
