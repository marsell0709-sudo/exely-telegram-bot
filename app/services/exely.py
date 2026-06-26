import time
import requests

from app.config import settings


class ExelyAPI:
    def __init__(self):
        self.token = None
        self.expire = 0

    def get_token(self):
        if self.token and time.time() < self.expire:
            return self.token

        response = requests.post(
            settings.EXELY_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.EXELY_CLIENT_ID,
                "client_secret": settings.EXELY_CLIENT_SECRET,
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        self.token = data["access_token"]
        self.expire = time.time() + data.get("expires_in", 900) - 30

        return self.token


exely = ExelyAPI()
