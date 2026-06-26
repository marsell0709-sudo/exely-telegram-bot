from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Найти квартиру")],
            [KeyboardButton(text="📅 Мои бронирования"), KeyboardButton(text="📞 Связаться с менеджером")],
            [KeyboardButton(text="ℹ️ Правила проживания")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
