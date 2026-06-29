import calendar
import re
from datetime import date, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.services.exely import exely

router = Router()

MONTHS_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}


class SearchState(StatesGroup):
    checkin = State()
    checkout = State()
    guests = State()


def format_price(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def clean_description(value: str, limit: int = 220) -> str:
    if not value:
        return "Описание скоро будет добавлено."

    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\\n", " ").replace("\n", " ").replace("\r", " ")
    value = re.sub(r"\s+", " ", value).strip()

    if len(value) > limit:
        value = value[:limit].strip() + "..."

    return value


def build_calendar(year: int, month: int, mode: str) -> InlineKeyboardMarkup:
    today = date.today()
    keyboard = []

    keyboard.append([
        InlineKeyboardButton(text="◀️", callback_data=f"cal_prev:{mode}:{year}:{month}"),
        InlineKeyboardButton(text=f"{MONTHS_RU[month]} {year}", callback_data="ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal_next:{mode}:{year}:{month}"),
    ])

    keyboard.append([
        InlineKeyboardButton(text="Пн", callback_data="ignore"),
        InlineKeyboardButton(text="Вт", callback_data="ignore"),
        InlineKeyboardButton(text="Ср", callback_data="ignore"),
        InlineKeyboardButton(text="Чт", callback_data="ignore"),
        InlineKeyboardButton(text="Пт", callback_data="ignore"),
        InlineKeyboardButton(text="Сб", callback_data="ignore"),
        InlineKeyboardButton(text="Вс", callback_data="ignore"),
    ])

    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                continue

            current_date = date(year, month, day)

            if current_date < today:
                row.append(InlineKeyboardButton(text="·", callback_data="ignore"))
            else:
                row.append(
                    InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"cal_date:{mode}:{current_date.isoformat()}",
                    )
                )

        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def guests_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="guests:1"),
                InlineKeyboardButton(text="2", callback_data="guests:2"),
                InlineKeyboardButton(text="3", callback_data="guests:3"),
            ],
            [
                InlineKeyboardButton(text="4", callback_data="guests:4"),
                InlineKeyboardButton(text="5", callback_data="guests:5"),
                InlineKeyboardButton(text="6", callback_data="guests:6"),
            ],
        ]
    )


@router.message(F.text == "🏠 Найти квартиру")
async def find_apartment(message: Message, state: FSMContext):
    today = date.today()
    await state.set_state(SearchState.checkin)

    await message.answer(
        "📅 Выберите дату заезда:",
        reply_markup=build_calendar(today.year, today.month, "checkin"),
    )


@router.callback_query(F.data.startswith("cal_prev:"))
async def calendar_prev(callback: CallbackQuery):
    _, mode, year, month = callback.data.split(":")
    year = int(year)
    month = int(month)

    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1

    await callback.message.edit_reply_markup(
        reply_markup=build_calendar(year, month, mode)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cal_next:"))
async def calendar_next(callback: CallbackQuery):
    _, mode, year, month = callback.data.split(":")
    year = int(year)
    month = int(month)

    if month == 12:
        year += 1
        month = 1
    else:
        month += 1

    await callback.message.edit_reply_markup(
        reply_markup=build_calendar(year, month, mode)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cal_date:"))
async def calendar_date(callback: CallbackQuery, state: FSMContext):
    _, mode, selected_date = callback.data.split(":")

    if mode == "checkin":
        await state.update_data(checkin=selected_date)
        await state.set_state(SearchState.checkout)

        selected = datetime.strptime(selected_date, "%Y-%m-%d").date()
        await callback.message.edit_text(
            f"✅ Дата заезда: {selected_date}\n\n📅 Теперь выберите дату выезда:",
            reply_markup=build_calendar(selected.year, selected.month, "checkout"),
        )

    elif mode == "checkout":
        data = await state.get_data()
        checkin = data.get("checkin")

        if selected_date <= checkin:
            await callback.answer("Дата выезда должна быть позже даты заезда.", show_alert=True)
            return

        await state.update_data(checkout=selected_date)
        await state.set_state(SearchState.guests)

        await callback.message.edit_text(
            f"✅ Даты: {checkin} — {selected_date}\n\n👥 Выберите количество гостей:",
            reply_markup=guests_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("guests:"))
async def choose_guests(callback: CallbackQuery, state: FSMContext):
    guests = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    await callback.message.edit_text("🔍 Ищу доступные апартаменты...")

    try:
        result = await exely.search_room_stays(
            arrival_date=data["checkin"],
            departure_date=data["checkout"],
            adults=guests,
        )
        room_types_map = await exely.get_room_types_map()
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка поиска в Exely:\n\n{e}")
        await callback.answer()
        return

    room_stays = result.get("roomStays", [])

    if not room_stays:
        await callback.message.answer("❌ На выбранные даты свободных вариантов нет.")
        await callback.answer()
        return

cheapest_by_room = {}

    for stay in room_stays:
        room_id = str(stay.get("roomType", {}).get("id"))

        price = (
            stay.get("total", {}).get("priceAfterTax")
            or stay.get("total", {}).get("priceBeforeTax")
            or 0
        )

        if not room_id:
            continue

        if room_id not in cheapest_by_room:
            cheapest_by_room[room_id] = stay
            continue

        old_price = (
            cheapest_by_room[room_id].get("total", {}).get("priceAfterTax")
            or cheapest_by_room[room_id].get("total", {}).get("priceBeforeTax")
            or 0
        )

        if price < old_price:
            cheapest_by_room[room_id] = stay

    for index, stay in enumerate(list(cheapest_by_room.values()), start=1):
        room_id = str(stay.get("roomType", {}).get("id"))
        room_info = room_types_map.get(room_id, {})

        room_name = room_info.get("name", f"Апартамент #{index}")
        description = clean_description(room_info.get("description", ""))
        images = room_info.get("images", [])
        image_url = images[0] if images else None

        price_total = (
            stay.get("total", {}).get("priceAfterTax")
            or stay.get("total", {}).get("priceBeforeTax")
            or 0
        )

        checkin_date = datetime.strptime(data["checkin"], "%Y-%m-%d").date()
        checkout_date = datetime.strptime(data["checkout"], "%Y-%m-%d").date()
        nights = (checkout_date - checkin_date).days
        price_per_night = price_total / nights if nights > 0 else price_total

        currency = stay.get("currencyCode", "UZS")
        currency_text = "сум" if currency == "UZS" else currency

        availability = stay.get("availability", 0)
        placement = stay.get("fullPlacementsName", "")
        booking_link = stay.get("bookingFormLink", "")

        text = (
    f"🏠 <b>{room_name}</b>\n\n"
    f"👥 Вместимость: {placement}\n"
    f"🌙 Ночей: {nights}\n\n"
    f"💵 За сутки: <b>{format_price(price_per_night)} {currency_text}</b>\n"
    f"💰 Итого: <b>{format_price(price_total)} {currency_text}</b>\n\n"
    f"📦 Свободно: {availability}\n\n"
    f"📝 {description}\n\n"
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

        if image_url:
            await callback.message.answer_photo(
                photo=image_url,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )

    await callback.answer()


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()
