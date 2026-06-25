# Exely Telegram Bot MVP

Telegram bot for rental/sublease business with Exely PMS integration placeholder.

## Features

- Client menu in Telegram
- Apartment search flow
- Booking request flow
- Manager channel notification
- Railway deployment via Docker
- Exely adapter ready for real API endpoints

## Railway Variables

Add these variables in Railway -> service -> Variables:

```env
BOT_TOKEN=your_telegram_bot_token
MANAGER_CHANNEL_ID=-1001234567890
EXELY_BASE_URL=https://api.example.com
EXELY_API_KEY=your_exely_api_key
EXELY_PROPERTY_ID=your_property_id
```

For first test, only `BOT_TOKEN` is required. Exely methods will return demo apartments until real API variables are added.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```
