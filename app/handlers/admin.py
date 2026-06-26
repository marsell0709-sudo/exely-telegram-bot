from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.exely import exely

router = Router()


@router.message(Command("testapi"))
async def test_api(message: Message):
    try:
        token = exely.get_token()

        await message.answer(
            "✅ Подключение к Exely успешно!\n\n"
            f"Токен получен.\n"
            f"Первые 30 символов:\n\n{token[:30]}..."
        )

    except Exception as e:
        await message.answer(
            f"❌ Ошибка подключения:\n\n{e}"
        )
