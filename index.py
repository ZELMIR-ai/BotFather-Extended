import os
import logging
import requests
from telegram import Update, LabeledPrice
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    PreCheckoutQueryHandler, filters, ContextTypes, ConversationHandler
)

# ==============================
# КЛЮЧИ
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# ==============================

logging.basicConfig(level=logging.INFO)

# Состояния
WAIT_PAYMENT, ASK_NAME, ASK_DESCRIPTION, ASK_FEATURES = range(4)

PRICE_STARS = 3

PRODUCT_LABELS = {
    "tgbot": "🤖 Telegram бот",
    "aibot": "🧠 ИИ бот",
    "site": "🌐 Сайт",
}


# ========== OpenRouter ==========
def ask_ai(prompt):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "google/gemini-2.0-flash-001",
            "messages": [
                {"role": "system", "content": "Ты опытный разработчик. Пиши чистый код с комментариями на русском."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 3000,
        }
    )

    return response.json()["choices"][0]["message"]["content"]


# ========== /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать!\n\n"
        "Доступные команды:\n"
        "/tgbot — создать Telegram бота\n"
        "/aibot — создать ИИ бота\n"
        "/site — создать сайт\n"
    )


# ========== Выбор ==========
async def start_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product_type):
    context.user_data["product_type"] = product_type
    label = PRODUCT_LABELS[product_type]

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=f"Создание: {label}",
        description=f"ИИ создаст для вас {label}",
        payload=f"create_{product_type}",
        currency="XTR",
        prices=[LabeledPrice(label=label, amount=PRICE_STARS)],
    )

    return WAIT_PAYMENT


async def tgbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_product(update, context, "tgbot")


async def aibot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_product(update, context, "aibot")


async def site(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_product(update, context, "site")


# ========== Оплата ==========
async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_type = context.user_data.get("product_type")
    label = PRODUCT_LABELS[product_type]

    await update.message.reply_text(
        f"✅ Оплата прошла!\n\nВведите название {label}:"
    )
    return ASK_NAME


# ========== Диалог ==========
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Опишите, что должен делать продукт:")
    return ASK_DESCRIPTION


async def ask_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("Доп функции или 'нет':")
    return ASK_FEATURES


async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["features"] = update.message.text

    name = context.user_data["name"]
    description = context.user_data["description"]
    features = context.user_data["features"]
    product_type = context.user_data["product_type"]

    prompts = {
        "tgbot": f"""Создай Telegram бота на Python.
Название: {name}
Описание: {description}
Функции: {features}""",

        "aibot": f"""Создай Telegram ИИ-бота на Python с OpenRouter API.
Название: {name}
Описание: {description}
Функции: {features}""",

        "site": f"""Создай сайт HTML/CSS/JS.
Название: {name}
Описание: {description}
Функции: {features}""",
    }

    await update.message.reply_text("⏳ Генерирую...")

    try:
        result = ask_ai(prompts[product_type])

        if len(result) > 4000:
            for i in range(0, len(result), 4000):
                await update.message.reply_text(result[i:i+4000])
        else:
            await update.message.reply_text(result)

    except Exception as e:
        logging.error(e)
        await update.message.reply_text("❌ Ошибка генерации")

    return ConversationHandler.END


# ========== Запуск ==========
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("tgbot", tgbot),
            CommandHandler("aibot", aibot),
            CommandHandler("site", site),
        ],
        states={
            WAIT_PAYMENT: [MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_description)],
            ASK_FEATURES: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(PreCheckoutQueryHandler(precheckout))

    print("✅ Запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
