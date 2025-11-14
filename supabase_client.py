from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
    raise RuntimeError("Faltan variables SUPABASE_URL o SUPABASE_SERVICE_ROLE")

supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
