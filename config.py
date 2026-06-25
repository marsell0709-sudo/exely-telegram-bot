from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    manager_channel_id: str | None = None
    exely_base_url: str | None = None
    exely_api_key: str | None = None
    exely_property_id: str | None = None

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


settings = Settings()
