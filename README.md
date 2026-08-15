# Telegram AI Agent Bot — Render Deployment Guide

## Kya hai ye
Ye ek Telegram bot hai jo Claude AI se connect hai. Aap bot ko Telegram par
message bhejenge, wo Claude se jawab lekar wapas bhej dega. Ye "background
worker" ki tarah 24/7 chalega — koi website/URL ki zaroorat nahi.

## Deploy karne ke steps (Render pe)

1. Render dashboard kholiye (jahan aapka `nifty-trading-bot-1` chal raha hai)
2. **New +** → **Background Worker** select kijiye (Web Service nahi — kyunki
   ye polling mode mein chalta hai, koi incoming URL request nahi leta)
3. Apna code GitHub repo se connect kijiye (ya "Public Git repository" option
   se agar aapne is folder ko GitHub par upload kiya hai)
4. Settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
   - **Region:** Singapore (same as your trading bot)
5. **Environment Variables** section mein ye do add kijiye:
   - `TELEGRAM_BOT_TOKEN` = BotFather se mila token
   - `ANTHROPIC_API_KEY` = aapki Anthropic API key
6. **Create Background Worker** dabaiye — Render apne aap build aur deploy
   kar dega

## Test kaise karein
- Render ke logs mein "Bot shuru ho raha hai (polling mode)..." dikhna
  chahiye
- Telegram app mein apne bot ko `/start` bhejiye
- Koi bhi message likh kar bhejiye, Claude ka jawab aana chahiye
- `/reset` bhejne se conversation history clear ho jayegi

## Aage kya
Is bot mein trading module aur automation module jodne ke liye, hum
`handle_message` function mein ek "router" jodenge jo decide karega ki
message trading-related hai ya general chat — us hisab se sahi module ko
call karega.
