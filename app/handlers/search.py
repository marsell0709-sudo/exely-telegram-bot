from datetime import datetime

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


def normalize_date(value: str) -> str:
    value = value.strip()

    if "." in value:
        return datetime.strptime(value, "%d.%m.%Y").strftime("%Y-%m-%d")

    return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")


@router.message(F.text == "🏠 Найти квартиру")
async def find_apartment(message: Message, state: FSMContext):
    await state.set_state(SearchState.checkin)
    await message.answer("Введите дату заезда в формате ДД.ММ.ГГГГ")


@router.message(SearchState.checkin)
async def get_checkin(message: Message, state: FSMContext):
    try:
        checkin = normalize_date(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Пример: 26.06.2026")
        return

    await state.update_data(checkin=checkin)
    await state.set_state(SearchState.checkout)
    await message.answer("Введите дату выезда в формате ДД.ММ.ГГГГ")


@router.message(SearchState.checkout)
async def get_checkout(message: Message, state: FSMContext):
    try:
        checkout = normalize_date(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Пример: 28.06.2026")
        return

    await state.update_data(checkout=checkout)
    await state.set_state(SearchState.guests)
    await message.answer("Сколько гостей будет проживать?")


@router.message(SearchState.guests)
async def get_guests(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    try:
        guests = int(message.text)
    except ValueError:
        await message.answer("Введите количество гостей числом.")
        return

    try:
        result = await exely.search_room_stays(
            arrival_date=data["checkin"],
            departure_date=data["checkout"],
            adults=guests,
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка поиска в Exely:\n\n{e}")
        return

    room_stays = result.get("roomStays", [])

    if not room_stays:
        await message.answer("❌ На выбранные даты свободных вариантов нет.")
        return

    for index, stay in enumerate(room_stays[:5], start=1):
        total = stay.get("total", {})
        price = total.get("priceBeforeTax", 0)
        currency = stay.get("currencyCode", "UZS")
        availability = stay.get("availability", 0)
        placement = stay.get("fullPlacementsName", "")
        booking_link = stay.get("bookingFormLink", "")

        text = (
            f"🏠 <b>Вариант #{index}</b>\n\n"
            f"👥 {placement}\n"
            f"💰 <b>{price:,.0f} {currency}</b>\n"
            f"📦 Осталось: {availability}\n\n"
            f"✅ Доступно для бронирования\n\n"
            f"🔗 <a href=\"{booking_link}\">Забронировать</a>"
        )

        await message.answer(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
