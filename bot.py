import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from deepgram_stt import transcribe
from openai_extract import VALID_PRIORITIES, extract_idea
from sheets_client import append_idea, ensure_header

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("idea-bot")

SHEET_URL = f"https://docs.google.com/spreadsheets/d/{config.GOOGLE_SHEET_ID}/edit"


def build_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Done", callback_data="done"),
                InlineKeyboardButton("Edit", callback_data="edit"),
            ],
            [
                InlineKeyboardButton("Regenerate", callback_data="regenerate"),
                InlineKeyboardButton("Cancel", callback_data="cancel"),
            ],
        ]
    )


def format_preview(idea: dict) -> str:
    return (
        f"Title: {idea['title']}\n\n"
        f"Video Idea: {idea['video_idea']}\n\n"
        f"Priority: {idea['priority']}\n\n"
        "Save this to the sheet?"
    )


def format_edit_template(idea: dict) -> str:
    return f"Title: {idea['title']}\nVideo Idea: {idea['video_idea']}\nPriority: {idea['priority']}"


def parse_edit(text: str, idea: dict) -> dict:
    """Parse a user-submitted 'Title: ...\\nVideo Idea: ...\\nPriority: ...' block,
    keeping any field that isn't recognized as-is from the current idea."""
    fields: dict = {}
    current_key = None
    buffer: list[str] = []

    def flush():
        if current_key is not None:
            fields[current_key] = "\n".join(buffer).strip()

    for line in text.splitlines():
        lower = line.strip().lower()
        if lower.startswith("title:"):
            flush()
            current_key = "title"
            buffer = [line.split(":", 1)[1].strip()]
        elif lower.startswith("video idea:"):
            flush()
            current_key = "video_idea"
            buffer = [line.split(":", 1)[1].strip()]
        elif lower.startswith("priority:"):
            flush()
            current_key = "priority"
            buffer = [line.split(":", 1)[1].strip()]
        elif current_key is not None:
            buffer.append(line)
    flush()

    updated = dict(idea)
    if fields.get("title"):
        updated["title"] = fields["title"]
    if fields.get("video_idea"):
        updated["video_idea"] = fields["video_idea"]
    if fields.get("priority"):
        priority = fields["priority"].strip().title()
        if priority in VALID_PRIORITIES:
            updated["priority"] = priority
    return updated


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send me a voice note (Hindi or English) describing a video idea and its priority "
        "(Highest / High / Medium / Low). I'll show you what I understood before saving it."
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice = update.message.voice or update.message.audio
    if voice is None:
        return

    context.user_data.pop("editing", None)
    status_msg = await update.message.reply_text("Listening to your voice note...")
    try:
        tg_file = await context.bot.get_file(voice.file_id)
        audio_bytes = bytes(await tg_file.download_as_bytearray())

        transcript = transcribe(audio_bytes, mimetype="audio/ogg")
        if not transcript.strip():
            await status_msg.edit_text("I couldn't hear anything in that voice note. Please try again.")
            return

        await status_msg.edit_text("Understanding your idea...")
        idea = extract_idea(transcript)

        context.user_data["transcript"] = transcript
        context.user_data["pending_idea"] = idea

        await status_msg.edit_text(format_preview(idea), reply_markup=build_keyboard())
    except Exception:
        logger.exception("Failed to process voice note")
        await status_msg.edit_text(
            "Something went wrong while processing your voice note. Please try again."
        )


async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    idea = context.user_data.get("pending_idea")
    transcript = context.user_data.get("transcript")

    if query.data == "cancel":
        context.user_data.pop("pending_idea", None)
        context.user_data.pop("transcript", None)
        context.user_data.pop("editing", None)
        await query.edit_message_text("Cancelled. Nothing was saved.")
        return

    if idea is None or transcript is None:
        await query.edit_message_text("This request has expired. Please send the voice note again.")
        return

    if query.data == "edit":
        context.user_data["editing"] = True
        await query.edit_message_text(
            "Send me the corrected text below. Keep the same three lines, edit whatever you want:\n\n"
            + format_edit_template(idea)
        )
        return

    if query.data == "regenerate":
        await query.edit_message_text("Regenerating...")
        try:
            new_idea = extract_idea(transcript)
        except Exception:
            logger.exception("Failed to regenerate idea")
            await query.edit_message_text("Couldn't regenerate. Please send the voice note again.")
            context.user_data.pop("pending_idea", None)
            context.user_data.pop("transcript", None)
            return
        context.user_data["pending_idea"] = new_idea
        await query.edit_message_text(format_preview(new_idea), reply_markup=build_keyboard())
        return

    if query.data == "done":
        try:
            append_idea(idea["title"], idea["video_idea"], idea["priority"])
        except Exception:
            logger.exception("Failed to save idea to sheet")
            await query.edit_message_text("Couldn't save to the sheet. Please try again.")
            return
        context.user_data.pop("pending_idea", None)
        context.user_data.pop("transcript", None)
        context.user_data.pop("editing", None)
        await query.edit_message_text(
            f"Sheet updated with your video idea. Priority: {idea['priority']}.\n\n"
            f"Title: {idea['title']}\n\n"
            f"{SHEET_URL}"
        )


async def handle_text_or_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text and context.user_data.get("editing"):
        idea = context.user_data.get("pending_idea")
        if idea is None:
            context.user_data.pop("editing", None)
            await update.message.reply_text("Nothing to edit right now. Please send a voice note first.")
            return

        updated = parse_edit(update.message.text, idea)
        context.user_data["pending_idea"] = updated
        context.user_data.pop("editing", None)
        await update.message.reply_text(format_preview(updated), reply_markup=build_keyboard())
        return

    await update.message.reply_text("Please send a voice note describing your video idea.")


def main() -> None:
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    ensure_header()

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(CallbackQueryHandler(handle_decision))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_text_or_other))

    logger.info("Bot starting (long polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
