import calendar
import re
from datetime import date, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, InputMediaPhoto

from app.config import settings
from app.services.exely import exely

router = Router()
booking_cache = {}

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
        return value[:limit].strip() + "..."

    return value


def get_price(stay: dict) -> float:
    total = stay.get("total", {})
    return total.get("priceAfterTax") or total.get("priceBeforeTax") or 0


def build_calendar(year: int, month: int, mode: str) -> InlineKeyboardMarkup:
    today = date.today()

    keyboard_buttons = [
    [
        InlineKeyboardButton(
            text="📩 Отправить заявку",
            callback_data=f"booking:{room_id}",
        )
    ]
]

if images:
    keyboard_buttons.append(
        [
            InlineKeyboardButton(
                text="🖼 Смотреть все фотографии",
                callback_data=f"gallery:{room_id}",
            )
        ]
    )

keyboard_buttons.append(
    [
        InlineKeyboardButton(
            text="🟢 Написать в WhatsApp",
            url="https://wa.me/998908225400",
        )
    ]
)

keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

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

    month -= 1

    if month == 0:
        month = 12
        year -= 1

    await callback.message.edit_reply_markup(
        reply_markup=build_calendar(year, month, mode)
    )

    await callback.answer()


@router.callback_query(F.data.startswith("cal_next:"))
async def calendar_next(callback: CallbackQuery):
    _, mode, year, month = callback.data.split(":")

    year = int(year)
    month = int(month)

    month += 1

    if month == 13:
        month = 1
        year += 1

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
            await callback.answer(
                "Дата выезда должна быть позже даты заезда.",
                show_alert=True,
            )
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
        rate_plans_map = await exely.get_rate_plans_map()

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка поиска в Exely:\n\n{e}")
        await callback.answer()
        return

    room_stays = result.get("roomStays", [])

    room_stays = [
        stay
        for stay in room_stays
        if str(stay.get("ratePlan", {}).get("id")) == settings.TELEGRAM_RATE_PLAN_ID
    ]

    if not room_stays:
        await callback.message.answer("❌ На выбранные даты свободных вариантов нет.")
        await callback.answer()
        return

    cheapest_by_room = {}

    for stay in room_stays:
        room_id = str(stay.get("roomType", {}).get("id"))
        price = get_price(stay)

        if not room_id:
            continue

        if room_id not in cheapest_by_room or price < get_price(cheapest_by_room[room_id]):
            cheapest_by_room[room_id] = stay

    sorted_stays = sorted(
        cheapest_by_room.values(),
        key=get_price,
    )

    checkin_date = datetime.strptime(data["checkin"], "%Y-%m-%d").date()
    checkout_date = datetime.strptime(data["checkout"], "%Y-%m-%d").date()
    nights = (checkout_date - checkin_date).days

    for index, stay in enumerate(sorted_stays, start=1):
        room_id = str(stay.get("roomType", {}).get("id"))
        room_info = room_types_map.get(room_id, {})

        rate_id = str(stay.get("ratePlan", {}).get("id"))
        rate_name = rate_plans_map.get(rate_id, {}).get("name", "Телеграм")

        room_name = room_info.get("name", f"Апартамент #{index}")
        description = clean_description(room_info.get("description", ""))

        images = room_info.get("images", [])
        image_url = images[0] if images else None

        price_total = get_price(stay)
        price_per_night = price_total / nights if nights > 0 else price_total

        currency = stay.get("currencyCode", "UZS")
        currency_text = "сум" if currency == "UZS" else currency

        availability = stay.get("availability", 0)
        placement = stay.get("fullPlacementsName", "")

        booking_cache[room_id] = {
            "room_name": room_name,
            "checkin": data["checkin"],
            "checkout": data["checkout"],
            "guests": guests,
            "nights": nights,
            "price_total": price_total,
            "currency_text": currency_text,
        }

        text = (
            f"🏠 <b>{room_name}</b>\n\n"
            f"👥 Вместимость: {placement}\n"
            f"🏷 Тариф: <b>{rate_name}</b>\n"
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
                        text="📩 Отправить заявку",
                        callback_data=f"booking:{room_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🟢 Написать в WhatsApp",
                        url="https://wa.me/998908225400",
                    )
                ],
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


@router.callback_query(F.data.startswith("booking:"))
async def booking_request(callback: CallbackQuery):
    room_id = callback.data.split(":")[1]

    booking = booking_cache.get(room_id)

    if not booking:
        await callback.answer(
            "Заявка устарела. Выполните поиск заново.",
            show_alert=True,
        )
        return

    user = callback.from_user

    username = f"@{user.username}" if user.username else "не указан"

    manager_text = (
        "🏠 <b>НОВАЯ ЗАЯВКА</b>\n\n"
        f"🏢 Апартамент: <b>{booking['room_name']}</b>\n"
        f"📅 Заезд: {booking['checkin']}\n"
        f"📅 Выезд: {booking['checkout']}\n"
        f"🌙 Ночей: {booking['nights']}\n"
        f"👥 Гостей: {booking['guests']}\n\n"
        f"💰 Стоимость: <b>{format_price(booking['price_total'])} {booking['currency_text']}</b>\n\n"
        "━━━━━━━━━━━━━━\n\n"
        "👤 <b>Клиент</b>\n"
        f"Имя: {user.full_name}\n"
        f"Username: {username}\n"
        f"Telegram ID: <code>{user.id}</code>"
    )

    await callback.bot.send_message(
        chat_id=settings.MANAGER_CHAT_ID,
        text=manager_text,
        parse_mode="HTML",
    )

    await callback.message.answer(
        "✅ Спасибо!\n\n"
        "Ваша заявка успешно отправлена.\n\n"
        "Наш менеджер свяжется с вами в ближайшее время."
    )

    await callback.answer("Заявка отправлена ✅")

@router.callback_query(F.data.startswith("gallery:"))
async def show_gallery(callback: CallbackQuery):
    room_id = callback.data.split(":")[1]
    booking = booking_cache.get(room_id)

    if not booking:
        await callback.answer(
            "Фотографии устарели. Выполните поиск заново.",
            show_alert=True,
        )
        return

    images = booking.get("images", [])

    if not images:
        await callback.answer(
            "Фотографии для этого апартамента не найдены.",
            show_alert=True,
        )
        return

    media = [
        InputMediaPhoto(media=image)
        for image in images[:10]
    ]

    await callback.message.answer_media_group(media=media)
    await callback.answer()
@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()
