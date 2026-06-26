from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.services.exely import exely

router = Router()


class SearchState(StatesGroup):
    checkin = State()
    checkout = State()
    guests = State()


@router.message(F.text == "🏠 Найти квартиру")
async def find_apartment(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchState.checkin)
    await message.answer("Введите дату заезда в формате ДД.ММ.ГГГГ")


@router.message(SearchState.checkin)
async def get_checkin(message: Message, state: FSMContext) -> None:
    await state.update_data(checkin=message.text)
    await state.set_state(SearchState.checkout)
    await message.answer("Введите дату выезда в формате ДД.ММ.ГГГГ")


@router.message(SearchState.checkout)
async def get_checkout(message: Message, state: FSMContext) -> None:
    await state.update_data(checkout=message.text)
    await state.set_state(SearchState.guests)
    await message.answer("Сколько гостей будет проживать?")


@router.message(SearchState.guests)
async def get_guests(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    try:
        guests = int(message.text)
    except ValueError:
        await message.answer("Введите количество гостей числом, например: 2")
        await state.set_state(SearchState.guests)
        return

    try:
        token = await exely.get_token()
    except Exception as e:
        await message.answer(f"❌ Ошибка подключения к Exely:\n\n{e}")
        return

    await message.answer(
        "✅ Подключение к Exely успешно.\n\n"
        "Поиск квартир через Search API добавим следующим этапом.\n"
        f"Гости: {guests}\n"
        f"Даты: {data['checkin']} — {data['checkout']}\n"
        f"Токен получен: {token[:20]}..."
    )
