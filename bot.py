import json
import os
import sys
import time

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
        "start": "Привет! Я — бот сервиса генерации видео и фото ИИ Сора. "
                 "Результат создаётся по референсу и промту. Выберите, как продолжить:",
        "btn_choose": "🎨 Выбрать референс",
        "btn_own": "➕ Добавить свой",
        "btn_no_ref": "🚫 Без референса",
        "btn_lang": "🌐 Язык / Language",
        "btn_back": "⬅️ Назад",
        "btn_video": "🎬 Видео",
        "btn_photo": "🖼 Фото",
        "pick_kind": "Что нужно сгенерировать?",
        "pick_ref": "Выберите референс:",
        "own": "Отправьте свой референс — фото или видео, на которое будет похож результат.",
        "need_file": "Нужно отправить фото или видео в качестве референса.",
        "pick_model": "Выберите модель для генерации:",
        "use_buttons": "Пожалуйста, выберите модель кнопкой выше.",
        "ask_prompt": "Отлично! Теперь отправьте промт — описание того, что должно быть на результате.",
        "need_text": "Промт нужно написать текстом.",
        "own_file": "ваш файл",
        "no_ref": "без референса",
        "done_video": "Спасибо! Заказ принят.\n\n"
                      "📋 Ваш заказ:\n"
                      "🎬 Тип: Видео\n"
                      "🖼 Референс: {ref}\n"
                      "🤖 Модель: {model}\n"
                      "✍️ Промт: {prompt}\n\n"
                      "Мы начали генерацию видео. Как только оно будет готово — пришлём его сюда в чат.",
        "done_photo": "Спасибо! Заказ принят.\n\n"
                      "📋 Ваш заказ:\n"
                      "🖼 Тип: Фото\n"
                      "🖼 Референс: {ref}\n"
                      "🤖 Модель: {model}\n"
                      "✍️ Промт: {prompt}\n\n"
                      "Мы начали генерацию фото. Как только оно будет готово — пришлём его сюда в чат.",
        "idle": "Напишите «привет» или нажмите /start, чтобы сделать заказ.",
        "blocked": "⛔ Вы временно заблокированы. Попробуйте снова через {mins} мин.",
        "no_credits": "💳 У сервиса закончились кредиты. Мы свяжемся с вами, когда генерация снова станет доступна.",
    },
    "en": {
        "start": "Hi! I'm the bot of the Sora AI video & photo generation service. "
                 "Results are created from a reference and a prompt. Choose how to continue:",
        "btn_choose": "🎨 Choose a reference",
        "btn_own": "➕ Add my own",
        "btn_no_ref": "🚫 No reference",
        "btn_lang": "🌐 Язык / Language",
        "btn_back": "⬅️ Back",
        "btn_video": "🎬 Video",
        "btn_photo": "🖼 Photo",
        "pick_kind": "What should be generated?",
        "pick_ref": "Choose a reference:",
        "own": "Send your own reference — a photo or video the result should look like.",
        "need_file": "Please send a photo or video as the reference.",
        "pick_model": "Choose a generation model:",
        "use_buttons": "Please choose a model with the buttons above.",
        "ask_prompt": "Great! Now send the prompt — a description of what the result should show.",
        "need_text": "The prompt must be written as text.",
        "own_file": "your file",
        "no_ref": "no reference",
        "done_video": "Thank you! Your order has been accepted.\n\n"
                      "📋 Your order:\n"
                      "🎬 Type: Video\n"
                      "🖼 Reference: {ref}\n"
                      "🤖 Model: {model}\n"
                      "✍️ Prompt: {prompt}\n\n"
                      "We have started generating your video. As soon as it is ready, we'll send it here in the chat.",
        "done_photo": "Thank you! Your order has been accepted.\n\n"
                      "📋 Your order:\n"
                      "🖼 Type: Photo\n"
                      "🖼 Reference: {ref}\n"
                      "🤖 Model: {model}\n"
                      "✍️ Prompt: {prompt}\n\n"
                      "We have started generating your photo. As soon as it is ready, we'll send it here in the chat.",
        "idle": "Write “hi” or press /start to place an order.",
        "blocked": "⛔ You are temporarily blocked. Try again in {mins} min.",
        "no_credits": "💳 The service has run out of credits. We'll contact you when generation is available again.",
    },
}

GREETINGS = {"привет", "начать", "старт", "start", "/start", "hi", "hello", "hey"}

ORDERS_FILE = "orders.json"
STATE_FILE = "state.json"

BLOCK_SECONDS = 60 * 60  # 1 час


# ---------- Хранилище ----------
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


orders = load_json(ORDERS_FILE, {})          # "id сообщения у админа" -> id клиента
blocks = load_json(STATE_FILE, {})            # "id клиента" -> timestamp до которого заблокирован

# "id сообщения с заказом" -> id клиента (для кнопок у админа)
order_owner = {k: v for k, v in orders.items()}


def save_orders():
    save_json(ORDERS_FILE, orders)
    save_json(STATE_FILE, blocks)


# ---------- Блокировки ----------
def is_blocked(user_id):
    until = blocks.get(str(user_id))
    if not until:
        return 0
    left = int(until - time.time())
    if left <= 0:
        blocks.pop(str(user_id), None)
        save_orders()
        return 0
    return left


def block_user(user_id, seconds=BLOCK_SECONDS):
    blocks[str(user_id)] = time.time() + seconds
    save_orders()


# ---------- Хелперы ----------
def lang_of(context):
    return context.user_data.get("lang", "ru")


def tr(context, key):
    return T[lang_of(context)][key]


def reset(context):
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


def kind_keyboard(context):
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(tr(context, "btn_video"), callback_data="kind:video"),
            InlineKeyboardButton(tr(context, "btn_photo"), callback_data="kind:photo"),
        ]]
    )


def main_keyboard(context):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(context, "btn_choose"), callback_data="choose")],
            [InlineKeyboardButton(tr(context, "btn_own"), callback_data="own")],
            [InlineKeyboardButton(tr(context, "btn_no_ref"), callback_data="noref")],
            [InlineKeyboardButton(tr(context, "btn_lang"), callback_data="chooselang")],
        ]
    )


def model_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(name, callback_data=f"model:{i}")] for i, name in enumerate(MODELS)]
    )


def admin_order_keyboard(client_id):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔒 Заблокировать на час", callback_data=f"admblock:{client_id}")],
            [InlineKeyboardButton("💳 Закончились кредиты", callback_data=f"admcredits:{client_id}")],
        ]
    )


# ---------- Обработчики ----------
async def send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset(context)
    msg = update.effective_message
    user = update.effective_user

    left = is_blocked(user.id)
    if left:
        mins = max(1, left // 60)
        await msg.reply_text(T[lang_of(context)]["blocked"].format(mins=mins))
        return

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

    # ---------- Кнопки админа ----------
    if data.startswith("admblock:"):
        if query.from_user.id != ADMIN_ID:
            return
        client_id = int(data.split(":")[1])
        block_user(client_id)
        await msg.reply_text(f"🔒 Пользователь {client_id} заблокирован на час.")
        try:
            await context.bot.send_message(
                client_id,
                "⛔ Вы временно заблокированы. Попробуйте снова через 60 мин.",
            )
        except Exception:
            pass
        return

    if data.startswith("admcredits:"):
        if query.from_user.id != ADMIN_ID:
            return
        client_id = int(data.split(":")[1])
        await msg.reply_text(f"💳 Отправлено «закончились кредиты» пользователю {client_id}.")
        try:
            await context.bot.send_message(
                client_id,
                "💳 У сервиса закончились кредиты. Мы свяжемся с вами, когда генерация снова станет доступна.",
            )
        except Exception:
            pass
        return

    # ---------- Кнопки клиента ----------
    user = query.from_user
    left = is_blocked(user.id)
    if left:
        mins = max(1, left // 60)
        await msg.reply_text(T[lang_of(context)]["blocked"].format(mins=mins))
        return

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

    elif data == "noref":
        reset(context)
        context.user_data["ref_text"] = tr(context, "no_ref")
        context.user_data["ref_msg"] = None
        context.user_data["step"] = "kind"
        await msg.reply_text(tr(context, "pick_kind"), reply_markup=kind_keyboard(context))

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
        context.user_data["step"] = "kind"
        await msg.reply_text(tr(context, "pick_kind"), reply_markup=kind_keyboard(context))

    elif data.startswith("kind:"):
        if context.user_data.get("step") != "kind":
            return
        context.user_data["kind"] = data.split(":")[1]  # "video" или "photo"
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
        if reply and str(reply.message_id) in order_owner:
            await context.bot.copy_message(
                chat_id=order_owner[str(reply.message_id)],
                from_chat_id=msg.chat_id,
                message_id=msg.message_id,
            )
            await msg.reply_text("Отправлено клиенту ✅")
        else:
            await msg.reply_text("Отвечай (Reply) на сообщение с заказом.")
        return

    # ---------- Сообщения от клиентов ----------
    left = is_blocked(user.id)
    if left:
        mins = max(1, left // 60)
        await msg.reply_text(T[lang_of(context)]["blocked"].format(mins=mins))
        return

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
        context.user_data["step"] = "kind"
        await msg.reply_text(tr(context, "pick_kind"), reply_markup=kind_keyboard(context))

    elif step == "kind":
        await msg.reply_text(tr(context, "pick_kind"), reply_markup=kind_keyboard(context))

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
        kind = context.user_data.get("kind", "video")
        lang = lang_of(context)

        if ref_msg:
            ref = await context.bot.copy_message(
                chat_id=ADMIN_ID,
                from_chat_id=msg.chat_id,
                message_id=ref_msg,
            )
            order_owner[str(ref.message_id)] = user.id
            orders[str(ref.message_id)] = user.id

        kind_label = "🎬 Видео" if kind == "video" else "🖼 Фото"

        info = await context.bot.send_message(
            ADMIN_ID,
            f"📥 Новый заказ от {name}\n"
            f"🆔 Клиент: {user.id}\n"
            f"🌐 Язык клиента: {lang}\n\n"
            f"📦 Тип: {kind_label}\n"
            f"🖼 Референс: {ref_text}\n"
            f"🤖 Модель: {model}\n"
            f"✍️ Промт:\n{msg.text}\n\n"
            f"Ответь (Reply) на это сообщение результатом, и клиент его получит.\n"
            f"Или используй кнопки ниже.",
            reply_markup=admin_order_keyboard(user.id),
        )
        order_owner[str(info.message_id)] = user.id
        orders[str(info.message_id)] = user.id
        save_orders()

        done_key = "done_video" if kind == "video" else "done_photo"
        await msg.reply_text(
            T[lang][done_key].format(ref=ref_text, model=model, prompt=msg.text)
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
