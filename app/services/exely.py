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

    async def get_content_test(self):
        token = await self.get_token()

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{settings.EXELY_BASE_URL}/content/v1/properties",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )

        response.raise_for_status()
        return response.json()

    async def get_property_full(self, property_id: str = "505576"):
        token = await self.get_token()

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{settings.EXELY_BASE_URL}/content/v1/properties/{property_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )

        response.raise_for_status()
        return response.json()

    async def get_room_types_map(self, property_id: str = "505576"):
        data = await self.get_property_full(property_id)

        room_types = data.get("roomTypes", [])
        result = {}

        for room in room_types:
            room_id = str(room.get("id"))
            images = room.get("images", [])

            result[room_id] = {
                "name": room.get("name", "Апартамент"),
                "description": room.get("description", ""),
                "images": [img.get("url") for img in images if img.get("url")],
            }

        return result

    async def search_room_stays(self, arrival_date: str, departure_date: str, adults: int):
        token = await self.get_token()

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{settings.EXELY_BASE_URL}/search/v1/properties/505576/room-stays",
                params={
                    "arrivalDate": arrival_date,
                    "departureDate": departure_date,
                    "adults": adults,
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )

        response.raise_for_status()
        return response.json()

    async def get_rate_plans_map(self, property_id: str = "505576"):
        data = await self.get_property_full(property_id)

        result = {}

        for rate in data.get("ratePlans", []):
            result[str(rate.get("id"))] = {
                "name": rate.get("name", "Неизвестный тариф"),
                "currency": rate.get("currency", ""),
            }

        return result


exely = ExelyAPI()
