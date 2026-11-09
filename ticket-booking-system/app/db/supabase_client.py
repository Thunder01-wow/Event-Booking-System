from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase() -> Client:
    """
    Shared client using the anon key. Respects RLS.
    Use ONLY for public reads (events, seats). Never sign a user in on this
    client: supabase-py would store that user's session on the shared object.
    """
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache
def get_supabase_admin() -> Client:
    """
    Client using the service role key. Bypasses RLS.
    Only for trusted server-side work (webhooks, price totals, dev confirm).
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_fresh_anon_client() -> Client:
    """Throwaway anon client. Used for signup/login so sessions never leak."""
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_user_client(token: str) -> Client:
    """
    Per-request client that acts as the logged-in user. Their JWT is sent to
    Postgres, so RLS applies and auth.uid() works inside hold_seat() etc.
    """
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(token)
    return client
