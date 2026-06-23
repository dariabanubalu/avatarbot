import os
import io
import logging
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

FRAMES = [
    {"id": "1", "name": "Лауреат премии", "file": "frames/1_laureat.png"},
    {"id": "2", "name": "Амбассадор",     "file": "frames/2_ambassador.png"},
    {"id": "3", "name": "Участница",      "file": "frames/3_uchastnitsa.png"},
]

SIZE = 1000

def apply_frame(user_photo_bytes: bytes, frame_path: str) -> bytes:
    photo = Image.open(io.BytesIO(user_photo_bytes)).convert("RGBA")
    w, h = photo.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    photo = photo.crop((left, top, left + min_side, top + min_side))
    photo = photo.resize((SIZE, SIZE), Image.LANCZOS)
    frame = Image.open(frame_path).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
    result = Image.alpha_composite(photo, frame)
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    buf.seek(0)
    return buf

def make_preview(user_photo_bytes: bytes) -> bytes:
    photo = Image.open(io.BytesIO(user_photo_bytes)).convert("RGBA")
    w, h = photo.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    photo = photo.crop((left, top, left + min_side, top + min_side))
    photo = photo.resize((SIZE, SIZE), Image.LANCZOS)

    THUMB = 460
    COLS = 2
    PADDING = 20
    ROWS = 2

    grid_w = COLS * THUMB + (COLS + 1) * PADDING
    grid_h = ROWS * THUMB + (ROWS + 1) * PADDING

    grid = Image.new("RGBA", (grid_w, grid_h), (245, 245, 245, 255))

    for i, f in enumerate(FRAMES):
        row = i // COLS
        col = i % COLS
        x = PADDING + col * (THUMB + PADDING)
        y = PADDING + row * (THUMB + PADDING)

        thumb_photo = photo.resize((THUMB, THUMB), Image.LANCZOS)
        frame_img = Image.open(f["file"]).convert("RGBA").resize((THUMB, THUMB), Image.LANCZOS)
        thumb = Image.alpha_composite(thumb_photo, frame_img)
        grid.paste(thumb, (x, y))

    buf = io.BytesIO()
    grid.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Рады видеть тебя в рядах сообщества «Женщины в современной индустрии».\n"
        "Добавь фирменную рамку к аватарке — отправь своё фото в квадратном формате, "
        "и я сделаю всё остальное.\n\n"
        "✨ И помни, уверенность — в наших силах!"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Обрабатываю фото, секунду... ⏳")

    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()
    context.user_data["photo"] = bytes(photo_bytes)

    preview_buf = make_preview(bytes(photo_bytes))

    keyboard = []
    row = []
    for i, f in enumerate(FRAMES):
        row.append(InlineKeyboardButton(f"{i+1}. {f['name']}", callback_data=f"frame_{f['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await update.message.reply_photo(
        photo=preview_buf,
        caption="Выбери рамку 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    frame_id = query.data.replace("frame_", "")
    frame = next((f for f in FRAMES if f["id"] == frame_id), None)
    if not frame:
        await query.message.reply_text("Рамка не найдена.")
        return

    photo_bytes = context.user_data.get("photo")
    if not photo_bytes:
        await query.message.reply_text("Сначала отправь фото!")
        return

    await query.message.reply_text("Накладываю рамку... 🎨")

    result_buf = apply_frame(photo_bytes, frame["file"])

    await query.message.reply_document(
        document=result_buf,
        filename=f"avatar_{frame['name']}.png",
        caption=f"✅ Готово! Рамка «{frame['name']}»\n\nОтправь новое фото, чтобы попробовать другую рамку.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Telegram-канал WIM", url="https://t.me/wim_industries_russia")]])
    )


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, отправь фото 📸")


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL, handle_other))
    app.run_polling()


if __name__ == "__main__":
    main()
