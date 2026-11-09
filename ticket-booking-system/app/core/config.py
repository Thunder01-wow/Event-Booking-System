from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    app_env: str = "development"
    app_port: int = 8000

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # Comma-separated list of origins the frontend is served from, so the
    # browser's CORS check allows requests from it. Vite's default dev port.
    frontend_origins: str = "http://localhost:5173"

    @property
    def frontend_origins_list(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


# Single settings instance, imported wherever config is needed.
settings = Settings()
