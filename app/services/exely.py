import time
import httpx

from app.config import settings


class ExelyAPI:
    def __init__(self):
        self.token = None
        self.expire = 0

    async def get_token(self):
        if self.token and time.time() < self.expire:
            return self.token

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                settings.EXELY_AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.EXELY_CLIENT_ID,
                    "client_secret": settings.EXELY_CLIENT_SECRET,
                },
            )

        response.raise_for_status()
        data = response.json()

        self.token = data["access_token"]
        self.expire = time.time() + data.get("expires_in", 900) - 30

        return self.token


exely = ExelyAPI()
