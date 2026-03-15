# config.py
# Loads environment variables from .env file
# Every other file imports settings from here — single source of truth

import os
from dotenv import load_dotenv

# load_dotenv() reads the .env file and puts values into os.environ
load_dotenv()

# os.getenv reads a value from environment, second param is default if not found
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")