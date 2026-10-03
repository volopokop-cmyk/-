import json
import os
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------- Переменные окружения ----------
# Значения приходят из секретов GitHub (BOT_TOKEN, ADMIN_ID).
# Если их нет — сразу выходим с понятной ошибкой, а не падаем в середине.
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_RAW = os.environ.get("ADMIN_ID")

if not BOT_TOKEN:
    print("ОШИБКА: переменная окружения BOT_TOKEN не задана.", file=sys.stderr)
    print("Добавь секрет BOT_TOKEN в GitHub: Settings → Secrets and variables → Actions.", file=sys.stderr)
    sys.exit(1)

if not ADMIN_ID_RAW or not ADMIN_ID_RAW.strip().isdigit():
    print("ОШИБКА: ADMIN_ID не задан или не является числом.", file=sys.stderr)
    print(f"Сейчас ADMIN_ID = {ADMIN_ID_RAW!r}", file=sys.stderr)
    print("В секрете ADMIN_ID должно быть только число, например 7012441944.", file=sys.stderr)
    sys.exit(1)

ADMIN_ID = int(ADMIN_ID_RAW.strip())

# ---------- Модели ----------
MODELS = [
    "Seedance 2.0 mini",
    "Seedance 2.0 fast",
    "Seedance 2.5",
    "Sora 3",
    "Happy Horse",
]

# ---------- Готовые референсы ----------
PRESETS = {
    "ru": ["Кино-стиль", "Аниме", "Реклама продукта", "Природа и пейзаж"],
    "en": ["Cinematic", "Anime", "Product ad", "Nature & landscape"],
}

# ---------- Тексты ----------
T = {
    "ru": {
        "start": "Привет! Я — бот сервиса генерации видео ИИ Сора. "
                 "Видео создаётся по референсу и промту. Выберите, как продолжить:",
        "btn_choose": "🎨 Выбрать референс",
        "btn_own": "➕ Добавить свой",
        "btn_lang": "🌐 Язык / Language",
        "btn_back": "⬅️ Назад",
        "pick_ref": "Выберите референс:",
        "own": "Отправьте свой референс — фото или видео, на которое будет похож результат.",
        "need_file": "Нужно отправить фото или видео в качестве референса.",
        "pick_model": "Выберите модель для генерации:",
        "use_buttons": "Пожалуйста, выберите модель кнопкой выше.",
        "ask_prompt": "Отлично! Теперь отправьте промт — описание того, что должно быть в видео.",
        "need_text": "Промт нужно написать текстом.",
        "own_file": "ваш файл",
        "done": "Спасибо! Заказ принят.\n\n"
                "📋 Ваш заказ:\n"
                "🖼 Референс: {ref}\n"
                "🤖 Модель: {model}\n"
                "✍️ Промт: {prompt}\n\n"
                "Мы начали генерацию видео. Как только оно будет готово — пришлём его сюда в чат.",
        "idle": "Напишите «привет» или нажмите /start, чтобы сделать заказ.",
    },
    "en": {
        "start": "Hi! I'm the bot of the Sora AI video generation service. "
                 "Videos are created from a reference and a prompt. Choose how to continue:",
        "btn_choose": "🎨 Choose a reference",
        "btn_own": "➕ Add my own",
        "btn_lang": "🌐 Язык / Language",
        "btn_back": "⬅️ Back",
        "pick_ref": "Choose a reference:",
        "own": "Send your own reference — a photo or video the result should look like.",
        "need_file": "Please send a photo or video as the reference.",
        "pick_model": "Choose a generation model:",
        "use_buttons": "Please choose a model with the buttons above.",
        "ask_prompt": "Great! Now send the prompt — a description of what the video should show.",
        "need_text": "The prompt must be written as text.",
        "own_file": "your file",
        "done": "Thank you! Your order has been accepted.\n\n"
                "📋 Your order:\n"
                "🖼 Reference: {ref}\n"
                "🤖 Model: {model}\n"
                "✍️ Prompt: {prompt}\n\n"
                "We have started generating your video. As soon as it is ready, we'll send it here in the chat.",
        "idle": "Write “hi” or press /start to place an order.",
    },
}

GREETINGS = {"привет", "начать", "старт", "start", "/start", "hi", "hello", "hey"}

ORDERS_FILE = "orders.json"


# ---------- Хранилище заказов ----------
def load_orders():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_orders():
    try:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


orders = load_orders()  # "id сообщения у админа" -> id клиента


# ---------- Хелперы ----------
def lang_of(context):
    return context.user_data.get("lang", "ru")


def tr(context, key):
    return T[lang_of(context)][key]


def reset(context):
    """Сбрасывает шаги заказа, но запоминает язык."""
    lang = context.user_data.get("lang")
    context.user_data.clear()
    if lang:
        context.user_data["lang"] = lang


# ---------- Клавиатуры ----------
def lang_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
        ]]
    )


def main_keyboard(context):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(context, "btn_choose"), callback_data="choose")],
            [InlineKeyboardButton(tr(context, "btn_own"), callback_data="own")],
            [InlineKeyboardButton(tr(context, "btn_lang"), callback_data="chooselang")],
        ]
    )


def model_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(name, callback_data=f"model:{i}")] for i, name in enumerate(MODELS)]
    )


# ---------- Обработчики ----------
async def send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset(context)
    msg = update.effective_message
    if "lang" not in context.user_data:
        await msg.reply_text("Выберите язык / Choose your language:", reply_markup=lang_keyboard())
    else:
        await msg.reply_text(tr(context, "start"), reply_markup=main_keyboard(context))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_start(update, context)


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    msg = query.message

    if data == "chooselang":
        await msg.reply_text("Выберите язык / Choose your language:", reply_markup=lang_keyboard())

    elif data.startswith("lang:"):
        reset(context)
        context.user_data["lang"] = data.split(":")[1]
        await msg.reply_text(tr(context, "start"), reply_markup=main_keyboard(context))

    elif data == "own":
        reset(context)
        context.user_data["step"] = "ref"
        await msg.reply_text(tr(context, "own"))

    elif data == "choose":
        presets = PRESETS[lang_of(context)]
        rows = [[InlineKeyboardButton(n, callback_data=f"preset:{i}")] for i, n in enumerate(presets)]
        rows.append([InlineKeyboardButton(tr(context, "btn_back"), callback_data="back")])
        await msg.reply_text(tr(context, "pick_ref"), reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("preset:"):
        idx = int(data.split(":")[1])
        reset(context)
        context.user_data["ref_text"] = PRESETS[lang_of(context)][idx]
        context.user_data["ref_msg"] = None
        context.user_data["step"] = "model"
        await msg.reply_text(tr(context, "pick_model"), reply_markup=model_keyboard())

    elif data == "back":
        await msg.reply_text(tr(context, "start"), reply_markup=main_keyboard(context))

    elif data.startswith("model:"):
        if context.user_data.get("step") != "model":
            return
        context.user_data["model"] = MODELS[int(data.split(":")[1])]
        context.user_data["step"] = "prompt"
        await msg.reply_text(tr(context, "ask_prompt"))


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    user = msg.from_user

    # ---------- Сообщения от админа: ответ на заказ ----------
    if user.id == ADMIN_ID:
        reply = msg.reply_to_message
        if reply and str(reply.message_id) in orders:
            await context.bot.copy_message(
                chat_id=orders[str(reply.message_id)],
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

    if text in GREETINGS and step != "prompt":
        await send_start(update, context)
        return

    if step == "ref":
        if not (msg.photo or msg.video or msg.document):
            await msg.reply_text(tr(context, "need_file"))
            return
        context.user_data["ref_msg"] = msg.message_id
        context.user_data["ref_text"] = tr(context, "own_file")
        context.user_data["step"] = "model"
        await msg.reply_text(tr(context, "pick_model"), reply_markup=model_keyboard())

    elif step == "model":
        await msg.reply_text(tr(context, "use_buttons"), reply_markup=model_keyboard())

    elif step == "prompt":
        if not msg.text:
            await msg.reply_text(tr(context, "need_text"))
            return

        name = f"{user.full_name} (@{user.username})" if user.username else user.full_name
        ref_text = context.user_data.get("ref_text", "—")
        ref_msg = context.user_data.get("ref_msg")
        model = context.user_data.get("model", "—")
        lang = lang_of(context)

        if ref_msg:
            ref = await context.bot.copy_message(
                chat_id=ADMIN_ID,
                from_chat_id=msg.chat_id,
                message_id=ref_msg,
            )
            orders[str(ref.message_id)] = user.id

        info = await context.bot.send_message(
            ADMIN_ID,
            f"📥 Новый заказ от {name}\n"
            f"🌐 Язык клиента: {lang}\n\n"
            f"🖼 Референс: {ref_text}\n"
            f"🤖 Модель: {model}\n"
            f"✍️ Промт:\n{msg.text}\n\n"
            f"Ответь (Reply) на это сообщение видео, и клиент его получит.",
        )
        orders[str(info.message_id)] = user.id
        save_orders()

        await msg.reply_text(
            T[lang]["done"].format(ref=ref_text, model=model, prompt=msg.text)
        )
        reset(context)

    else:
        await msg.reply_text(tr(context, "idle"))


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(~filters.COMMAND, handle))
    print("Бот запущен", flush=True)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
