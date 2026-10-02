from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8990054244:AAERsDeEzq2tuATUwah04NWMdJlYgRUtYLA"
ADMIN_ID = 7012441944  # твой Telegram ID

orders = {}  # id сообщения у тебя -> id клиента


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["step"] = "ref"
    await update.message.reply_text("Привет! Пришли референс (фото или видео).")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = msg.from_user

    # --- сообщения от тебя: ответ видео на заказ ---
    if user.id == ADMIN_ID:
        reply = msg.reply_to_message
        if reply and reply.message_id in orders:
            await context.bot.copy_message(
                chat_id=orders[reply.message_id],
                from_chat_id=msg.chat_id,
                message_id=msg.message_id,
            )
            await msg.reply_text("Отправлено клиенту ✅")
        else:
            await msg.reply_text("Отвечай (Reply) на сообщение с заказом.")
        return

    # --- сообщения от клиентов ---
    step = context.user_data.get("step")

    if step == "ref":
        if not (msg.photo or msg.video or msg.document):
            await msg.reply_text("Нужно фото или видео в качестве референса.")
            return
        context.user_data["ref_msg"] = msg.message_id
        context.user_data["step"] = "prompt"
        await msg.reply_text("Отлично! Теперь пришли промпт — описание того, что нужно.")

    elif step == "prompt":
        if not msg.text:
            await msg.reply_text("Промпт нужно написать текстом.")
            return
        name = f"{user.full_name} (@{user.username})" if user.username else user.full_name

        ref = await context.bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=msg.chat_id,
            message_id=context.user_data["ref_msg"],
        )
        info = await context.bot.send_message(
            ADMIN_ID, f"Новый заказ от {name}\n\nПромпт:\n{msg.text}"
        )
        orders[ref.message_id] = user.id
        orders[info.message_id] = user.id

        context.user_data.clear()
        await msg.reply_text("Заказ принят ✅ Ждите, примерно 10 минут.")

    else:
        await msg.reply_text("Нажми /start, чтобы сделать заказ.")


app = (
    Application.builder()
    .token(TOKEN)
    .connect_timeout(30)
    .read_timeout(30)
    .build()

)
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(~filters.COMMAND, handle))
print("Бот запущен")
app.run_polling()