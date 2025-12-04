from supabase import create_client, Client
from config import settings, logger

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

def get_supabase() -> Client:
    return supabase

def check_db_connection() -> bool:
    try:

        result = supabase.table("users").select("user_id").limit(1).execute()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def init_db() -> None:
    logger.info("Checking database connection...")
    if check_db_connection():
        logger.info("Database is ready")
    else:
        logger.error("Database connection failed - please check your configuration")
