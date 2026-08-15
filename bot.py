import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

# In-memory conversation history per chat (resets if the service restarts)
conversation_history = {}


def ask_gemini(chat_id: int, user_message: str) -> str:
    """Send the user's message (with recent history) to Gemini and return the reply text."""
    history = conversation_history.get(chat_id, [])
    history.append({"role": "user", "parts": [{"text": user_message}]})

    # Keep only the last 10 messages to control context size
    history = history[-10:]

    headers = {"content-type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {"contents": history}

    try:
        response = requests.post(
            GEMINI_API_URL, headers=headers, params=params, json=payload, timeout=30
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        reply_text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            reply_text = "".join(part.get("text", "") for part in parts)
        if not reply_text:
            reply_text = "Maaf kijiye, jawab generate nahi ho paaya."
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        reply_text = "Kuch technical dikkat aa gayi, thodi der baad phir try kijiye."

    history.append({"role": "model", "parts": [{"text": reply_text}]})
    conversation_history[chat_id] = history

    return reply_text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! Main aapka AI agent hoon. Mujhe kuch bhi likh kar poochh sakte hain."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history.pop(chat_id, None)
    await update.message.reply_text("Conversation reset ho gayi hai.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    reply_text = ask_gemini(chat_id, user_message)
    await update.message.reply_text(reply_text)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable set nahi hai.")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable set nahi hai.")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot shuru ho raha hai (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
