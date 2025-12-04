from app.config import SUPABASE_KEY, SUPABASE_URL, setup_logger
from supabase import Client, create_client

logger = setup_logger(__name__)
# logger.info(f"Supabase key: {SUPABASE_KEY}")
supabase: Client = create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)


# Custom Exception for Supabase
class DatabaseError(Exception):
    def __init__(self, msg: str | None):
        message = f"Supabase Error: {msg}"
        super().__init__(message)


def get_supabase() -> Client:
    return supabase


def check_db_connection() -> bool:
    try:

        result = supabase.rpc("ping").execute()

        if result.data.lower() == "pong":
            logger.info("Database connection successful", "BLUE")
            return True
        else:
            raise

    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


check_db_connection()
