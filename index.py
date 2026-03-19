import os
import logging
import requests
from telegram import Update, LabeledPrice
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler,
    PreCheckoutQueryHandler
)

# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# ==============================

logging.basicConfig(level=logging.INFO)

# Состояния диалога
ASK_NAME, ASK_DESCRIPTION, ASK_FEATURES, WAIT_CODE_PAYMENT = range(4)

# Типы продуктов
PRODUCT_LABELS = {
    "tgbot": "🤖 Telegram бот",
    "aibot": "🧠 ИИ бот",
    "site":  "🌐 Сайт",
}


def ask_ai(prompt: str) -> str:
    """Запрос к OpenRouter API"""
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {"role": "system", "content": "Ты опытный разработчик. Пиши чистый рабочий код с комментариями на русском языке."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 3000,
            },
            timeout=60
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"OpenRouter error: {e}")
        return None


# ========== /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в *BotFather Extended!*\n\n"
        "Я помогу вам создать:\n"
        "🤖 Telegram бота\n"
        "🧠 ИИ бота\n"
        "🌐 Одностраничный сайт\n\n"
        "💬 Обычный вопрос — *1 ⭐*\n"
        "🛠 Генерация кода — *3 ⭐*\n\n"
        "Используйте /newbot чтобы начать!",
        parse_mode="Markdown"
    )


# ========== /newbot ==========
async def newbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *Что хотите создать?*\n\n"
        "/tgbot — 🤖 Telegram бот\n"
        "/aibot — 🧠 ИИ бот\n"
        "/site  — 🌐 Сайт\n\n"
        "Стоимость: *3 ⭐ Stars*",
        parse_mode="Markdown"
    )


# ========== Оплата за обычное сообщение (1 звезда) ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Любое текстовое сообщение вне диалога — запрашиваем 1 звезду"""
    context.user_data["pending_message"] = update.message.text

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="💬 Ответ ИИ",
        description="Получить ответ от ИИ на ваш вопрос",
        payload="msg_payment",
        currency="XTR",
        prices=[LabeledPrice(label="Ответ ИИ", amount=1)],
    )


# ========== Начало диалога для кода ==========
async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE, product_type: str):
    context.user_data["product_type"] = product_type
    label = PRODUCT_LABELS[product_type]
    await update.message.reply_text(
        f"✅ Создаём *{label}* — стоимость *3 ⭐*\n\n"
        f"📝 Как будет называться ваш продукт?",
        parse_mode="Markdown"
    )
    return ASK_NAME


async def tgbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await begin(update, context, "tgbot")

async def aibot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await begin(update, context, "aibot")

async def site_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await begin(update, context, "site")


# ========== Имя ==========
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "✏️ Отлично! Теперь опишите *что должен делать* ваш продукт?\n\n"
        "Например: _отвечать на вопросы, принимать заказы, показывать меню..._",
        parse_mode="Markdown"
    )
    return ASK_DESCRIPTION


# ========== Описание ==========
async def ask_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text(
        "⚙️ Какие *дополнительные функции* нужны?\n\n"
        "Например: _кнопки, меню, оплата, регистрация..._\n"
        "Или напишите *нет* если базового достаточно.",
        parse_mode="Markdown"
    )
    return ASK_FEATURES


# ========== Запрос оплаты за код (3 звезды) ==========
async def request_code_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["features"] = update.message.text
    product_type = context.user_data["product_type"]
    label = PRODUCT_LABELS[product_type]

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=f"Создание: {label}",
        description=f"ИИ создаст для вас {label} по вашим требованиям",
        payload=f"code_{product_type}",
        currency="XTR",
        prices=[LabeledPrice(label=label, amount=3)],
    )
    return WAIT_CODE_PAYMENT


# ========== PreCheckout (обязательно подтверждаем) ==========
async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


# ========== Успешная оплата ==========
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = update.message.successful_payment.invoice_payload

    # --- Оплата за обычное сообщение ---
    if payload == "msg_payment":
        user_text = context.user_data.get("pending_message", "")
        if not user_text:
            await update.message.reply_text("❌ Не удалось найти ваш вопрос. Напишите снова.")
            return

        await update.message.reply_text("⏳ Думаю...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        result = ask_ai(user_text)
        if result:
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("❌ Ошибка ИИ. Попробуйте ещё раз.")
        return

    # --- Оплата за генерацию кода ---
    if payload.startswith("code_"):
        product_type = payload.replace("code_", "")
        label = PRODUCT_LABELS.get(product_type, "продукт")

        name = context.user_data.get("name", "")
        description = context.user_data.get("description", "")
        features = context.user_data.get("features", "")

        await update.message.reply_text("⏳ Генерирую код... Подождите 20-30 секунд!")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        prompts = {
            "tgbot": f"""Создай готовый код Telegram бота на Python с библиотекой python-telegram-bot.
Название: {name}
Описание: {description}
Функции: {features}
Дай полный рабочий код с комментариями на русском языке и README с инструкцией по запуску.""",

            "aibot": f"""Создай готовый код Telegram ИИ-бота на Python с python-telegram-bot и OpenAI-совместимым API.
Название: {name}
Описание: {description}
Функции: {features}
Дай полный рабочий код с комментариями на русском языке и README с инструкцией по запуску.""",

            "site": f"""Создай красивый современный одностраничный сайт на HTML/CSS/JS.
Название: {name}
Описание: {description}
Функции: {features}
Дай один полный HTML файл со встроенным CSS и JS. Современный красивый дизайн.""",
        }

        result = ask_ai(prompts[product_type])

        if not result:
            await update.message.reply_text("❌ Ошибка генерации. Попробуйте /newbot ещё раз.")
            return

        if len(result) > 4000:
            parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
            for i, part in enumerate(parts):
                await update.message.reply_text(
                    f"📦 *Часть {i+1}/{len(parts)}:*\n\n```\n{part}\n```",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                f"✅ *{label} готов!*\n\n```\n{result}\n```",
                parse_mode="Markdown"
            )

        await update.message.reply_text(
            f"🎉 Ваш *{label}* создан!\n\nХотите создать ещё? Используйте /newbot",
            parse_mode="Markdown"
        )


# ========== Отмена ==========
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено. Используйте /newbot чтобы начать заново.")
    return ConversationHandler.END


# ========== Запуск ==========
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Хендлеры для генерации кода (3 звезды)
    for cmd, handler in [("tgbot", tgbot), ("aibot", aibot_cmd), ("site", site_cmd)]:
        conv = ConversationHandler(
            entry_points=[CommandHandler(cmd, handler)],
            states={
                ASK_NAME:          [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
                ASK_DESCRIPTION:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_description)],
                ASK_FEATURES:      [MessageHandler(filters.TEXT & ~filters.COMMAND, request_code_payment)],
                WAIT_CODE_PAYMENT: [MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newbot", newbot))
    app.add_handler(PreCheckoutQueryHandler(precheckout))

    # Обычные сообщения — 1 звезда (вне диалога)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    print("✅ BotFather Extended запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
