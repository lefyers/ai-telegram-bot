import os
import asyncio
import time
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import google.generativeai as genai
from dotenv import load_dotenv
from knowledge_base import COMPANY_INFO

load_dotenv()

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "ВАШ_TELEGRAM_TOKEN_ЗДЕСЬ")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ВАШ_GEMINI_API_KEY_ЗДЕСЬ")
MAX_HISTORY = 10        # максимум сообщений в истории диалога
RATE_LIMIT_SECONDS = 2  # минимум секунд между запросами одного пользователя
# ================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = f"""Ты — AI-ассистент интернет-магазина «Центр Красок #1» (centr-krasok.kz).
Ты отвечаешь на вопросы клиентов о компании, товарах, услугах, доставке и контактах.

ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленной информации о компании ниже.
2. Если вопрос не связан с компанией — вежливо скажи, что ты помогаешь только по вопросам «Центр Красок #1».
3. Если информации нет в базе знаний — честно скажи об этом и предложи обратиться: +7 (777) 292-84-01 или info@centr-krasok.kz.
4. Не выдумывай товары, цены, адреса или факты, которых нет в базе знаний.
5. Отвечай по-русски, дружелюбно и кратко. Можешь использовать emoji.
6. При вопросах о ценах — скажи, что актуальные цены на сайте centr-krasok.kz.

ИНФОРМАЦИЯ О КОМПАНИИ:
{COMPANY_INFO}
"""

# Хранилище истории диалогов: user_id -> список сообщений Gemini
conversation_history: dict[int, list] = {}

# Хранилище времени последнего запроса для rate limit: user_id -> timestamp
last_request_time: dict[int, float] = {}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    # --- Rate limit ---
    now = time.time()
    if user_id in last_request_time:
        elapsed = now - last_request_time[user_id]
        if elapsed < RATE_LIMIT_SECONDS:
            await update.message.reply_text("⏳ Пожалуйста, подождите секунду перед следующим вопросом.")
            return
    last_request_time[user_id] = now

    # --- Защита от пустых и слишком длинных сообщений ---
    if not user_text:
        return
    if len(user_text) > 1000:
        await update.message.reply_text("📝 Сообщение слишком длинное. Пожалуйста, задайте вопрос короче.")
        return

    # --- Инициализация истории ---
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        history = conversation_history[user_id]
        chat = model.start_chat(history=history)

        # Системный промпт добавляется к КАЖДОМУ запросу для надёжности
        full_prompt = f"{SYSTEM_PROMPT}\n\nВопрос пользователя: {user_text}"

        response = chat.send_message(full_prompt)
        answer = response.text

        # Ограничиваем историю
        conversation_history[user_id] = chat.history[-MAX_HISTORY:]

        await update.message.reply_text(answer)

    except Exception as e:
        logger.error(f"Ошибка Gemini для user {user_id}: {e}")
        await update.message.reply_text(
            "😔 Произошла ошибка. Попробуйте снова или свяжитесь с нами напрямую:\n"
            "📞 +7 (777) 292-84-01\n"
            "✉️ info@centr-krasok.kz"
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    # Сброс истории и rate limit при /start
    conversation_history[user_id] = []
    last_request_time.pop(user_id, None)

    await update.message.reply_text(
        "👋 Привет! Я AI-ассистент магазина «Центр Красок #1».\n\n"
        "Задайте любой вопрос о компании — отвечу сразу!\n\n"
        "Примеры:\n"
        "• Чем занимается компания?\n"
        "• Где находится офис в Алматы?\n"
        "• Какие бренды красок есть?\n"
        "• Как оформить доставку?\n"
        "• Есть ли скидки для дизайнеров?"
    )


def main():
    if "ВАШ_" in TELEGRAM_TOKEN:
        print("❌ Укажите TELEGRAM_TOKEN в файле .env!")
        return
    if "ВАШ_" in GEMINI_API_KEY:
        print("❌ Укажите GEMINI_API_KEY в файле .env!")
        return

    print("🚀 Бот запускается...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен! Нажмите Ctrl+C для остановки.")
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
