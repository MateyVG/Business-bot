"""Връзка със Supabase."""
import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


@lru_cache(maxsize=2)
def get_client(use_service_key: bool = False) -> Client:
    """Връща Supabase клиент.

    use_service_key=True се ползва САМО при качване на данни (ingest),
    защото service_role ключът заобикаля Row Level Security.
    За четене в приложението ползваме anon ключа.
    """
    url = os.environ["SUPABASE_URL"]
    if use_service_key:
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_ANON_KEY"]
    else:
        key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)
