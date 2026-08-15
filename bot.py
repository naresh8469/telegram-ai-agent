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
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-6"

# In-memory conversation history per chat (resets if the service restarts)
conversation_history = {}


def ask_claude(chat_id: int, user_message: str) -> str:
    """Send the user's message (with recent history) to Claude and return the reply text."""
    history = conversation_history.get(chat_id, [])
    history.append({"role": "user", "content": user_message})

    # Keep only the last 10 messages to control context size
    history = history[-10:]

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1000,
        "messages": history,
    }

    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        reply_text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        if not reply_text:
            reply_text = "Maaf kijiye, jawab generate nahi ho paaya."
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        reply_text = "Kuch technical dikkat aa gayi, thodi der baad phir try kijiye."

    history.append({"role": "assistant", "content": reply_text})
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

    reply_text = ask_claude(chat_id, user_message)
    await update.message.reply_text(reply_text)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable set nahi hai.")
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable set nahi hai.")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot shuru ho raha hai (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
