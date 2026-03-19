import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# ==============================

logging.basicConfig(level=logging.INFO)

# Состояния диалога
ASK_NAME, ASK_DESCRIPTION, ASK_FEATURES = range(3)

# Типы продуктов
PRODUCT_LABELS = {
    "tgbot": "🤖 Telegram бот",
    "aibot": "🧠 ИИ бот",
    "site": "🌐 Сайт",
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
        "Используйте /newbot чтобы начать!",
        parse_mode="Markdown"
    )


# ========== /newbot ==========
async def newbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *Что хотите создать?*\n\n"
        "/tgbot — 🤖 Telegram бот\n"
        "/aibot — 🧠 ИИ бот\n"
        "/site — 🌐 Сайт",
        parse_mode="Markdown"
    )


# ========== Начало диалога ==========
async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE, product_type: str):
    context.user_data["product_type"] = product_type
    label = PRODUCT_LABELS[product_type]
    await update.message.reply_text(
        f"✅ Отлично! Создаём *{label}*\n\n"
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


# ========== Генерация ==========
async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["features"] = update.message.text

    name = context.user_data["name"]
    description = context.user_data["description"]
    features = context.user_data["features"]
    product_type = context.user_data["product_type"]
    label = PRODUCT_LABELS[product_type]

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
        return ConversationHandler.END

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

    return ConversationHandler.END


# ========== Отмена ==========
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено. Используйте /newbot чтобы начать заново.")
    return ConversationHandler.END


# ========== Запуск ==========
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    for cmd, handler in [("tgbot", tgbot), ("aibot", aibot_cmd), ("site", site_cmd)]:
        conv = ConversationHandler(
            entry_points=[CommandHandler(cmd, handler)],
            states={
                ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
                ASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_description)],
                ASK_FEATURES: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newbot", newbot))

    print("✅ BotFather Extended запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
