import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, PreCheckoutQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from groq import Groq

# ==============================
# ВСТАВЬТЕ ВАШИ КЛЮЧИ СЮДА
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# ==============================

logging.basicConfig(level=logging.INFO)
client = Groq(api_key=GROQ_API_KEY)

# Состояния диалога
CHOOSE_TYPE, WAIT_PAYMENT, ASK_NAME, ASK_DESCRIPTION, ASK_FEATURES, GENERATING = range(6)

# Цена в Stars
PRICE_STARS = 3

# Типы продуктов
PRODUCT_LABELS = {
    "tgbot": "🤖 Telegram бот",
    "aibot": "🧠 ИИ бот",
    "site": "🌐 Сайт",
}


# ========== /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в *BotFather Extended!*\n\n"
        "Я помогу вам создать:\n"
        "🤖 Telegram бота\n"
        "🧠 ИИ бота\n"
        "🌐 Одностраничный сайт\n\n"
        "Используйте команду /newbot чтобы начать.\n"
        "Стоимость создания: всего *3 Stars* ⭐",
        parse_mode="Markdown"
    )


# ========== /newbot ==========
async def newbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🤖 TG Бот", callback_data="tgbot")],
        [InlineKeyboardButton("🧠 ИИ Бот", callback_data="aibot")],
        [InlineKeyboardButton("🌐 Сайт", callback_data="site")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🛠 *Что хотите создать?*\n\n"
        "Выберите тип — каждый стоит *3 Stars* ⭐",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSE_TYPE


# ========== Выбор типа ==========
async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_type = query.data
    context.user_data["product_type"] = product_type
    label = PRODUCT_LABELS[product_type]

    # Отправляем инвойс на оплату Stars
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=f"Создание: {label}",
        description=f"ИИ создаст для вас {label} по вашим требованиям",
        payload=f"create_{product_type}",
        currency="XTR",  # XTR = Telegram Stars
        prices=[LabeledPrice(label=label, amount=PRICE_STARS)],
    )
    return WAIT_PAYMENT


# ========== Проверка оплаты ==========
async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)


# ========== Успешная оплата ==========
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_type = context.user_data.get("product_type", "tgbot")
    label = PRODUCT_LABELS[product_type]

    await update.message.reply_text(
        f"✅ Оплата {PRICE_STARS} Stars получена!\n\n"
        f"Начинаем создание: *{label}*\n\n"
        f"📝 Как будет называться ваш {label}?",
        parse_mode="Markdown"
    )
    return ASK_NAME


# ========== Имя ==========
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "✏️ Отлично! Теперь опишите *что должен делать* ваш продукт?\n\n"
        "Например: _отвечать на вопросы клиентов, принимать заказы, показывать меню..._",
        parse_mode="Markdown"
    )
    return ASK_DESCRIPTION


# ========== Описание ==========
async def ask_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text(
        "⚙️ Какие *дополнительные функции* нужны?\n\n"
        "Например: _кнопки, меню, оплата, регистрация, каталог..._\n"
        "Или напишите *'нет'* если базового функционала достаточно.",
        parse_mode="Markdown"
    )
    return ASK_FEATURES


# ========== Функции → Генерация ==========
async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["features"] = update.message.text

    name = context.user_data["name"]
    description = context.user_data["description"]
    features = context.user_data["features"]
    product_type = context.user_data["product_type"]
    label = PRODUCT_LABELS[product_type]

    await update.message.reply_text("⏳ Генерирую для вас код... Это займёт 10-20 секунд!")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Промпты для разных типов
    prompts = {
        "tgbot": f"""Создай готовый код Telegram бота на Python с библиотекой python-telegram-bot.
Название бота: {name}
Описание: {description}
Дополнительные функции: {features}
Дай полный рабочий код с комментариями на русском языке. Включи README с инструкцией по запуску.""",

        "aibot": f"""Создай готовый код Telegram ИИ-бота на Python с библиотекой python-telegram-bot и Groq API (модель llama3-8b-8192).
Название бота: {name}
Описание: {description}
Дополнительные функции: {features}
Дай полный рабочий код с комментариями на русском языке. Включи README с инструкцией по запуску.""",

        "site": f"""Создай красивый одностраничный сайт на HTML/CSS/JS.
Название: {name}
Описание: {description}
Дополнительные функции: {features}
Дай полный рабочий HTML файл со встроенным CSS и JS. Сделай современный дизайн.""",
    }

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Ты опытный разработчик. Пиши чистый, рабочий код с комментариями на русском языке."},
                {"role": "user", "content": prompts[product_type]}
            ],
            max_tokens=3000,
        )

        result = response.choices[0].message.content

        # Разбиваем на части если текст длинный (лимит Telegram 4096 символов)
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
            f"🎉 Ваш *{label}* создан!\n\n"
            "Если нужны правки или хотите создать ещё — используйте /newbot\n\n"
            "По вопросам: напишите владельцу бота.",
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text("❌ Ошибка генерации. Попробуйте ещё раз через /newbot")
        logging.error(f"Groq error: {e}")

    return ConversationHandler.END


# ========== Отмена ==========
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено. Используйте /newbot чтобы начать заново.")
    return ConversationHandler.END


# ========== Запуск ==========
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newbot", newbot)],
        states={
            CHOOSE_TYPE: [CallbackQueryHandler(choose_type)],
            WAIT_PAYMENT: [MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_description)],
            ASK_FEATURES: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(PreCheckoutQueryHandler(precheckout))

    print("✅ BotFather Extended запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
