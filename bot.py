import os
import logging
import requests
from flask import Flask, request

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable set nahi hai.")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable set nahi hai.")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

app = Flask(__name__)

# In-memory conversation history per chat (resets if the service restarts)
conversation_history = {}


def ask_groq(chat_id: int, user_message: str) -> str:
    """Send the user's message (with recent history) to Groq and return the reply text."""
    history = conversation_history.get(chat_id, [])
    history.append({"role": "user", "content": user_message})

    # Keep only the last 10 messages to control context size
    history = history[-10:]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "content-type": "application/json",
    }
    payload = {"model": GROQ_MODEL, "messages": history}

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        reply_text = ""
        if choices:
            reply_text = choices[0].get("message", {}).get("content", "")
        if not reply_text:
            reply_text = "Maaf kijiye, jawab generate nahi ho paaya."
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        reply_text = "Kuch technical dikkat aa gayi, thodi der baad phir try kijiye."

    history.append({"role": "assistant", "content": reply_text})
    conversation_history[chat_id] = history

    return reply_text


def send_telegram_message(chat_id: int, text: str):
    try:
        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except Exception as e:
        logger.error(f"Telegram send error: {e}")


@app.route("/", methods=["GET"])
def health_check():
    # Render (aur uptime pingers) is URL ko ping karke service ko jagaye rakhte hain
    return "Bot is running", 200


@app.route(f"/webhook/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    logger.info(f"Update mila: {update}")

    message = update.get("message")
    if not message:
        return "ok", 200

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text == "/start":
        send_telegram_message(
            chat_id,
            "Namaste! Main aapka AI agent hoon. Mujhe kuch bhi likh kar poochh sakte hain.",
        )
    elif text == "/reset":
        conversation_history.pop(chat_id, None)
        send_telegram_message(chat_id, "Conversation reset ho gayi hai.")
    elif text:
        reply_text = ask_groq(chat_id, text)
        send_telegram_message(chat_id, reply_text)

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
