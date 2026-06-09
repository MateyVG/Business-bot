"""Връзка със Supabase."""
import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

import config

load_dotenv()


@lru_cache(maxsize=2)
def get_client(use_service_key: bool = False) -> Client:
    """Връща Supabase клиент.

    URL и anon ключът са публични (само четене) и идват по подразбиране от
    config.py, така че четенето работи още след клониране. Стойност в .env,
    ако има, има приоритет.

    use_service_key=True се ползва САМО при качване на данни (ingest), защото
    service_role ключът заобикаля Row Level Security. Той е таен и НЯМА
    стойност по подразбиране — трябва да е в .env (SUPABASE_SERVICE_KEY).
    """
    url = os.environ.get("SUPABASE_URL") or config.SUPABASE_URL
    anon = os.environ.get("SUPABASE_ANON_KEY") or config.SUPABASE_ANON_KEY
    if use_service_key:
        key = os.environ.get("SUPABASE_SERVICE_KEY") or anon
    else:
        key = anon
    return create_client(url, key)
