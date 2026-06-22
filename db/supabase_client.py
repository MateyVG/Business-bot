"""Връзка със Supabase."""
import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

import config

load_dotenv()


def _secret(name: str) -> str | None:
    """Чете таен/конфигурационен ключ от средата или от Streamlit secrets.

    Приоритет: променлива на средата (.env локално) -> st.secrets (Streamlit
    Cloud). Така един и същ код работи и локално, и при деплой, без да внасяме
    твърда зависимост от streamlit (CLI-то няма нужда от него).
    """
    val = os.environ.get(name)
    if val:
        return val
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return None


@lru_cache(maxsize=2)
def get_client(use_service_key: bool = False) -> Client:
    """Връща Supabase клиент.

    URL и anon ключът са публични (само четене) и идват по подразбиране от
    config.py, така че четенето работи още след клониране. Стойност в .env или
    Streamlit secrets, ако има, има приоритет.

    use_service_key=True се ползва САМО при писане (качване/редакция), защото
    service_role ключът заобикаля Row Level Security. Той е таен и НЯМА
    стойност по подразбиране — слага се в .env (локално) или в Streamlit
    secrets (при деплой), НИКОГА в git.
    """
    url = _secret("SUPABASE_URL") or config.SUPABASE_URL
    anon = _secret("SUPABASE_ANON_KEY") or config.SUPABASE_ANON_KEY
    if use_service_key:
        key = _secret("SUPABASE_SERVICE_KEY") or anon
    else:
        key = anon
    return create_client(url, key)


def has_service_key() -> bool:
    """Има ли service_role ключ — т.е. дали приложението може да ПИШЕ в базата.

    Без него writes-ите (качване/редакция на данни) ще се отрежат от RLS.
    """
    return bool(_secret("SUPABASE_SERVICE_KEY"))


def has_secret(name: str) -> bool:
    """Дали даден ключ е наличен (в средата или Streamlit secrets)."""
    return bool(_secret(name))


def get_secret(name: str) -> str | None:
    """Връща стойността на ключ от средата или Streamlit secrets (или None)."""
    return _secret(name)
