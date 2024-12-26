import os
from dotenv import load_dotenv
import openai

load_dotenv()

class Config:
    ODDS_API_KEY = os.getenv("ODDS_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    openai.api_key = OPENAI_API_KEY

    if not ODDS_API_KEY:
        raise ValueError("ODDS_API_KEY is not set in the environment or .env file")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in the environment or .env file")
