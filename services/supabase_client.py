from supabase import Client, create_client
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL') or ''
key = os.getenv('SUPABASE_SERVICE_ROLE') or ''


if not url or not url.startswith("https"):
    raise ValueError(
        f"CRITICAL: SUPABASE_URL is missing or invalid in your .env file. Got: '{url}'")

if not key:
    raise ValueError(
        "CRITICAL: SUPABASE_SERVICE_ROLE_KEY is missing from your .env file.")

supabase = create_client(url, key)
