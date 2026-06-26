from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.main_menu import main_menu

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "Здравствуйте! Я бот для бронирования квартир в Ташкенте.\n\n"
        "Выберите действие в меню ниже.",
        reply_markup=main_menu(),
    )


@router.message(lambda message: message.text == "ℹ️ Правила проживания")
async def rules_handler(message: Message) -> None:
    await message.answer(
        "Правила проживания:\n"
        "• Заезд после 14:00\n"
        "• Выезд до 12:00\n"
        "• Курение в квартире запрещено\n"
        "• Паспорт/ID обязателен при заселении"
    )


@router.message(lambda message: message.text == "📞 Связаться с менеджером")
async def contact_handler(message: Message) -> None:
    await message.answer("Напишите ваш вопрос, менеджер скоро свяжется с вами.")


@router.message(lambda message: message.text == "📅 Мои бронирования")
async def bookings_handler(message: Message) -> None:
    await message.answer("Пока у вас нет активных бронирований.")
