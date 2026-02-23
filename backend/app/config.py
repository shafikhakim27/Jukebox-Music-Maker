from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Jukebox Music Maker API'
    secret_key: str = 'dev-secret-change-me'
    algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60 * 24

    database_url: str = 'sqlite:///./jukebox.db'
    uploads_dir: str = './uploads'

    admin_username: str = 'admin'
    admin_password: str = 'admin1234'
    host_password: str = 'host1234'
    shared_user_password: str = 'jukebox1234'

    queue_rate_limit_count: int = 10
    queue_rate_limit_seconds: int = 30


settings = Settings()
