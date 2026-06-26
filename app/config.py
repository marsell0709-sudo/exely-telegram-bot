import os

class Settings:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    EXELY_AUTH_URL = os.getenv(
        "EXELY_AUTH_URL",
        "https://connect.hopenapi.com/auth/token"
    )

    EXELY_BASE_URL = os.getenv(
        "EXELY_BASE_URL",
        "https://connect.hopenapi.com/api"
    )

    EXELY_CLIENT_ID = os.getenv("EXELY_CLIENT_ID")
    EXELY_CLIENT_SECRET = os.getenv("EXELY_CLIENT_SECRET")


settings = Settings()
