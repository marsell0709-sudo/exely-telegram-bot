class ExelyClient:
    """Заглушка для Exely PMS API. Реальные методы подключим на следующем этапе."""

    async def search_availability(self, checkin: str, checkout: str, guests: int) -> list[dict]:
        return [
            {
                "id": "demo-1",
                "title": "Демо квартира в Ташкенте",
                "price": "650 000 сум/сутки",
                "description": "Тестовый объект. Позже данные будут приходить из Exely PMS.",
            }
        ]
