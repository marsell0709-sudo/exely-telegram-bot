from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

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


def format_price(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


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

    cheapest_by_room = {}

    for stay in room_stays:
        room_id = stay.get("roomType", {}).get("id")
            room_types_map = await exely.get_room_types_map()
        price = stay.get("total", {}).get("priceBeforeTax", 0)

        if not room_id:
            continue

        if room_id not in cheapest_by_room:
            cheapest_by_room[room_id] = stay
        else:
            old_price = cheapest_by_room[room_id].get("total", {}).get("priceBeforeTax", 0)
            if price < old_price:
                cheapest_by_room[room_id] = stay

   for index, stay in enumerate(list(cheapest_by_room.values())[:5], start=1):

    room_id = str(stay.get("roomType", {}).get("id"))
    room_info = room_types_map.get(room_id, {})

    room_name = room_info.get("name", f"Апартамент #{index}")
    description = room_info.get("description", "")

    short_description = description.replace("\n", " ").replace("\r", "")

    if len(short_description) > 250:
        short_description = short_description[:250] + "..."

    price = stay.get("total", {}).get("priceBeforeTax", 0)
    currency = stay.get("currencyCode", "UZS")
    availability = stay.get("availability", 0)
    placement = stay.get("fullPlacementsName", "")
    booking_link = stay.get("bookingFormLink", "")

    text = (
        f"🏠 <b>{room_name}</b>\n\n"
        f"👥 {placement}\n"
        f"💰 <b>{format_price(price)} {currency}</b>\n"
        f"📦 Осталось: {availability}\n\n"
        f"📝 {short_description}\n\n"
        f"✅ Доступно для бронирования"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Забронировать",
                    url=booking_link,
                )
            ]
        ]
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )
