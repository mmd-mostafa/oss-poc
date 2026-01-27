"""
Configuration file for RRC SR Degradation Detection System.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default configuration values
DEFAULT_PERCENTILE = 10
DEFAULT_TIME_BEFORE_MIN = 30
DEFAULT_TIME_AFTER_MIN = 30
DEFAULT_LLM_MODEL = "gpt-4o-mini"

# OpenAI API key (loaded from .env file)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Model configuration
LLM_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]

# Processing configuration
MIN_DEGRADATION_DURATION_MINUTES = 5

# File paths (can be overridden)
DEFAULT_KPI_PATH = "data/Fake data.xlsx"
DEFAULT_ALARMS_PATH = "data/Fake alarms.json"
