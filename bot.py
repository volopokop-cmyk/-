import json
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = "8990054244:AAERsDeEzq2tuATUwah04NWMdJlYgRUtYLA"
ADMIN_ID =7012441944   # твой Telegram ID (число из @userinfobot)

# Список готовых референсов для кнопки «Выбрать референс».
# Впиши свои названия, каждое станет отдельной кнопкой.
PRESETS = [
    "Кино-стиль",
    "Аниме",
    "Реклама продукта",
    "Природа и пейзаж",
]

TEXT_START = (
    "Привет! Я — бот сервиса генерации видео ИИ Сора. "
    "Видео создаётся по референсу и промту. Выберите, как продолжить:"
)
TEXT_OWN = "Отправьте свой референс — фото или видео, на которое будет похож результат."
TEXT_ASK_PROMPT = "Отлично! Теперь отправьте промт — описание того, что должно быть в видео."
TEXT_DONE = (
    "Спасибо! Заказ принят.\n\n"
    "📋 Ваш заказ:\n"
    "🖼 Референс: {ref}\n"
    "✍️ Промт: {prompt}\n\n"
    "Мы начали генерацию видео. Как только оно будет готово — пришлём его сюда в чат."
)

GREETINGS = {"привет", "начать", "старт", "start", "/start"}

# Заказы сохраняются в файл, чтобы после перезапуска бота
# можно было отвечать на старые заказы.
ORDERS_FILE = "orders.json"


def load_orders():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_orders():
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f)


orders = load_orders()  # "id сообщения у админа" -> id клиента


def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎨 Выбрать референс", callback_data="choose")],
            [InlineKeyboardButton("➕ Добавить свой", callback_data="own")],
        ]
    )


async def send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text(TEXT_START, reply_markup=main_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_start(update, context)


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "own":
        context.user_data.clear()
        context.user_data["step"] = "ref"
        await query.message.reply_text(TEXT_OWN)

    elif data == "choose":
        rows = [
            [InlineKeyboardButton(name, callback_data=f"preset:{i}")]
            for i, name in enumerate(PRESETS)
        ]
        rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
        await query.message.reply_text(
            "Выберите референс:", reply_markup=InlineKeyboardMarkup(rows)
        )

    elif data.startswith("preset:"):
        idx = int(data.split(":")[1])
        context.user_data.clear()
        context.user_data["ref_text"] = PRESETS[idx]
        context.user_data["ref_msg"] = None
        context.user_data["step"] = "prompt"
        await query.message.reply_text(TEXT_ASK_PROMPT)

    elif data == "back":
        await query.message.reply_text(TEXT_START, reply_markup=main_keyboard())


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = msg.from_user

    # ---------- Сообщения от админа (тебя): ответ на заказ ----------
    if user.id == ADMIN_ID:
        reply = msg.reply_to_message
        if reply and str(reply.message_id) in orders:
            client_id = orders[str(reply.message_id)]
            # copy_message отправляет клиенту ТОЛЬКО само видео,
            # без пометок «переслано от...»
            await context.bot.copy_message(
                chat_id=client_id,
                from_chat_id=msg.chat_id,
                message_id=msg.message_id,
            )
            await msg.reply_text("Отправлено клиенту ✅")
        else:
            await msg.reply_text("Отвечай (Reply) на сообщение с заказом.")
        return

    # ---------- Сообщения от клиентов ----------
    step = context.user_data.get("step")
    text = (msg.text or "").strip().lower()

    # «привет», «начать» и т.п. открывают меню (кроме момента, когда ждём промт)
    if text in GREETINGS and step != "prompt":
        await send_start(update, context)
        return

    if step == "ref":
        if not (msg.photo or msg.video or msg.document):
            await msg.reply_text("Нужно отправить фото или видео в качестве референса.")
            return
        context.user_data["ref_msg"] = msg.message_id
        context.user_data["ref_text"] = "ваш файл"
        context.user_data["step"] = "prompt"
        await msg.reply_text(TEXT_ASK_PROMPT)

    elif step == "prompt":
        if not msg.text:
            await msg.reply_text("Промт нужно написать текстом.")
            return

        name = f"{user.full_name} (@{user.username})" if user.username else user.full_name
        ref_text = context.user_data.get("ref_text", "—")
        ref_msg = context.user_data.get("ref_msg")

        # Тебе приходит референс (если свой) и отдельно сообщение с промтом
        if ref_msg:
            ref = await context.bot.copy_message(
                chat_id=ADMIN_ID,
                from_chat_id=msg.chat_id,
                message_id=ref_msg,
            )
            orders[str(ref.message_id)] = user.id

        info = await context.bot.send_message(
            ADMIN_ID,
            f"📥 Новый заказ от {name}\n\n"
            f"🖼 Референс: {ref_text}\n"
            f"✍️ Промт:\n{msg.text}\n\n"
            f"Ответь (Reply) на это сообщение видео, и клиент его получит.",
        )
        orders[str(info.message_id)] = user.id