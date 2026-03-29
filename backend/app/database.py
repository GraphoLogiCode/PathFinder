"""
PathFinder — Supabase Client

Returns None gracefully if credentials aren't configured,
allowing the backend to run without Supabase during early phases.
"""

from __future__ import annotations

from supabase import create_client, Client

from app.config import settings


def get_supabase() -> Client | None:
    """Create and return a Supabase client, or None if not configured."""
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)
