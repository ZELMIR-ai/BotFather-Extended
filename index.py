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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

ASK_NAME, ASK_DESCRIPTION, ASK_FEATURES, WAIT_CODE_PAYMENT = range(4)

PRODUCT_LABELS = {
    "tgbot": "🤖 Telegram бот",
    "aibot": "🧠 ИИ бот",
    "site":  "🌐 Сайт",
}

# Хранилище: user_id -> {"free_used": bool, "msg_count": int, "code_count": int}
user_data_store = {}

KING_SYSTEM_PROMPT = (
    "Ты — Король. Мудрый, величественный и немного высокомерный правитель знаний. "
    "Ты отвечаешь на вопросы с царским достоинством, иногда используешь торжественные фразы, "
    "обращаешься к собеседнику как 'подданный' или 'смертный'. "
    "Твои ответы умные, но с характером. Пишешь на русском языке."
)


def get_user_store(user_id: int) -> dict:
    if user_id not in user_data_store:
        user_data_store[user_id] = {"free_used": False, "msg_count": 0, "code_count": 0}
    return user_data_store[user_id]


def ask_ai(prompt: str, system: str = None) -> str:
    if system is None:
        system = "Ты опытный разработчик. Пиши чистый рабочий код с комментариями на русском языке."
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
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 3000,
            },
            timeout=60
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        return None


# ========== /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "подданный"
    get_user_store(user_id)  # инициализируем

    await update.message.reply_text(
        f"👑 Добро пожаловать, *{name}!*\n\n"
        "Я — *BotFather Extended*, слуга Короля технологий.\n\n"
        "🛠 *Создание проектов:*\n"
        "🤖 /tgbot — Telegram бот\n"
        "🧠 /aibot — ИИ бот\n"
        "🌐 /site — Сайт\n"
        "Стоимость: *10 ⭐ Stars*\n\n"
        "👑 *Спросить Короля:*\n"
        "Напишите любой вопрос боту\n"
        "Первый вопрос — *бесплатно* 🎁\n"
        "Далее — *3 ⭐ Stars*\n\n"
        "📊 /stats — ваша статистика\n"
        "📖 /newbot — создать проект",
        parse_mode="Markdown"
    )


# ========== /newbot ==========
async def newbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *Что хотите создать?*\n\n"
        "/tgbot — 🤖 Telegram бот\n"
        "/aibot — 🧠 ИИ бот\n"
        "/site  — 🌐 Сайт\n\n"
        "Стоимость: *10 ⭐ Stars*",
        parse_mode="Markdown"
    )


# ========== /stats ==========
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    store = get_user_store(user_id)
    free = "использован ✅" if store["free_used"] else "доступен 🎁"
    await update.message.reply_text(
        f"📊 *Ваша статистика:*\n\n"
        f"💬 Вопросов задано: *{store['msg_count']}*\n"
        f"🛠 Проектов создано: *{store['code_count']}*\n"
        f"🎁 Бесплатный вопрос: {free}",
        parse_mode="Markdown"
    )


# ========== Начало диалога ==========
async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE, product_type: str):
    context.user_data["product_type"] = product_type
    label = PRODUCT_LABELS[product_type]
    await update.message.reply_text(
        f"✅ Создаём *{label}* — стоимость *10 ⭐*\n\n"
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


# ========== Запрос оплаты за код (10 звёзд) ==========
async def request_code_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["features"] = update.message.text
    product_type = context.user_data["product_type"]
    label = PRODUCT_LABELS[product_type]

    try:
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title=f"Создание: {label}",
            description=f"ИИ создаст для вас {label} по вашим требованиям",
            payload=f"code_{product_type}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=label, amount=10)],
        )
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        await update.message.reply_text(f"❌ Ошибка при создании счёта: {e}")
        return ConversationHandler.END

    return WAIT_CODE_PAYMENT


# ========== PreCheckout ==========
async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


# ========== Успешная оплата за КОД ==========
async def paid_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    store = get_user_store(user_id)

    product_type = context.user_data.get("product_type", "tgbot")
    label = PRODUCT_LABELS.get(product_type, "продукт")
    name = context.user_data.get("name", "")
    description = context.user_data.get("description", "")
    features = context.user_data.get("features", "")

    await update.message.reply_text("⏳ Генерирую код... Подождите 20-30 секунд!")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    prompts = {
        "tgbot": f"Создай готовый код Telegram бота на Python с библиотекой python-telegram-bot.\nНазвание: {name}\nОписание: {description}\nФункции: {features}\nДай полный рабочий код с комментариями на русском языке и README.",
        "aibot": f"Создай готовый код Telegram ИИ-бота на Python с python-telegram-bot и OpenAI-совместимым API.\nНазвание: {name}\nОписание: {description}\nФункции: {features}\nДай полный рабочий код с комментариями на русском языке и README.",
        "site":  f"Создай красивый современный одностраничный сайт на HTML/CSS/JS.\nНазвание: {name}\nОписание: {description}\nФункции: {features}\nДай один полный HTML файл со встроенным CSS и JS.",
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

    store["code_count"] += 1
    await update.message.reply_text(
        f"🎉 Ваш *{label}* создан!\n\nХотите создать ещё? Используйте /newbot",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# ========== Обычное сообщение — Король ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    store = get_user_store(user_id)
    text = update.message.text

    # Первое сообщение бесплатно
    if not store["free_used"]:
        store["free_used"] = True
        store["msg_count"] += 1
        await update.message.reply_text("🎁 *Ваш первый вопрос — бесплатно!*\n\n⏳ Король думает...", parse_mode="Markdown")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        result = ask_ai(text, system=KING_SYSTEM_PROMPT)
        if result:
            await update.message.reply_text(f"👑 *Король отвечает:*\n\n{result}\n\n_Следующий вопрос — 3 ⭐_", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Король занят. Попробуйте позже.")
        return

    # Остальные — 3 звезды
    context.user_data["pending_message"] = text
    try:
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title="👑 Ответ Короля",
            description="Получить мудрый ответ от Короля",
            payload="msg_payment",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Ответ Короля", amount=3)],
        )
    except Exception as e:
        logger.error(f"Message invoice error: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


# ========== Успешная оплата за СООБЩЕНИЕ ==========
async def paid_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    store = get_user_store(user_id)

    user_text = context.user_data.get("pending_message", "")
    if not user_text:
        await update.message.reply_text("❌ Не удалось найти ваш вопрос. Напишите снова.")
        return

    await update.message.reply_text("👑 Король думает...", parse_mode="Markdown")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    result = ask_ai(user_text, system=KING_SYSTEM_PROMPT)
    store["msg_count"] += 1

    if result:
        await update.message.reply_text(f"👑 *Король отвечает:*\n\n{result}", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Король занят. Попробуйте позже.")


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
                ASK_NAME:          [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
                ASK_DESCRIPTION:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_description)],
                ASK_FEATURES:      [MessageHandler(filters.TEXT & ~filters.COMMAND, request_code_payment)],
                WAIT_CODE_PAYMENT: [MessageHandler(filters.SUCCESSFUL_PAYMENT, paid_code)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
            allow_reentry=True,
        )
        app.add_handler(conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newbot", newbot))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, paid_message))

    print("✅ BotFather Extended запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
