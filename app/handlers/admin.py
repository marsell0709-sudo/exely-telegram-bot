from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.exely import exely

router = Router()


@router.message(Command("testapi"))
async def test_api(message: Message):
    try:
        token = await exely.get_token()

        await message.answer(
            "✅ Подключение к Exely успешно!\n\n"
            f"Токен получен.\n"
            f"Первые 30 символов:\n\n{token[:30]}..."
        )

    except Exception as e:
        await message.answer(
            f"❌ Ошибка подключения:\n\n{e}"
        )


@router.message(Command("content"))
async def test_content(message: Message):
    try:
        data = await exely.get_content_test()

        await message.answer(
            "✅ Content API ответил успешно.\n\n"
            f"Тип ответа: {type(data).__name__}\n"
            f"Первые данные:\n{str(data)[:1000]}"
        )

    except Exception as e:
        await message.answer(
            f"❌ Ошибка Content API:\n\n{e}"
        )
