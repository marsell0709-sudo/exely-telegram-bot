from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.services.exely import ExelyClient

router = Router()
exely = ExelyClient()


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

    apartments = await exely.search_availability(data["checkin"], data["checkout"], guests)
    if not apartments:
        await message.answer("На эти даты свободных объектов нет.")
        return

    for item in apartments:
        await message.answer(
            f"🏠 {item['title']}\n"
            f"💰 {item['price']}\n"
            f"📝 {item['description']}\n\n"
            "Для бронирования напишите менеджеру. На следующем этапе добавим кнопку бронирования."
        )
