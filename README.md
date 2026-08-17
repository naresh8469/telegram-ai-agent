# Telegram AI Agent Bot — Render Free Web Service Deployment Guide

## Kya hai ye
Ye ek Telegram bot hai jo Groq AI se connect hai. Ye "Web Service" ki tarah
chalta hai (free, card nahi chahiye) aur Telegram se "webhook" ke zariye
messages receive karta hai.

## Groq API Key kaise banayein
1. **console.groq.com** kholiye aur account bana lijiye (email se sign up
   ho jata hai, card nahi chahiye)
2. Left menu mein **API Keys** par jaiye
3. **Create API Key** dabaiye, koi bhi naam dijiye
4. Jo key milegi wo `gsk_...` se shuru hogi — use turant copy karke rakh
   lijiye (dobara poori key nahi dikhegi)

## Render pe Deploy karne ke steps

1. Render dashboard kholiye, **New +** → **Web Service** chuniye
   *(Background Worker NAHI — Web Service, jisme free option hai)*
2. Apna GitHub repo connect kijiye jisme ye teen files hain (`bot.py`,
   `requirements.txt`, `README.md`)
3. Settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn bot:app`
   - **Instance Type:** **Free**
4. **Environment Variables** mein add kijiye:
   - `TELEGRAM_BOT_TOKEN` = BotFather se mila token
   - `GROQ_API_KEY` = aapki Groq API key (gsk_ se shuru hogi)
5. **Create Web Service** dabaiye — deploy hone do

6. Deploy poora hone ke baad, Render aapko ek URL dega, jaise:
   `https://thorai-agent-bot.onrender.com`
   Ise copy kar lijiye.

## Webhook set karna (ek baar ka kaam)

Deploy hone ke baad, apna bot Telegram se connect karne ke liye webhook set
karna hoga. Apne phone ke browser mein ye URL kholiye (apna token aur
Render URL daal kar):

```
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<aapka-render-url>.onrender.com/webhook/<TELEGRAM_BOT_TOKEN>
```

Jaise agar token `123:ABC` hai aur Render URL `thorai-agent-bot.onrender.com`
hai, to:

```
https://api.telegram.org/bot123:ABC/setWebhook?url=https://thorai-agent-bot.onrender.com/webhook/123:ABC
```

Browser mein `{"ok":true,"result":true,...}` dikhna chahiye — iska matlab
webhook set ho gaya.

## Test kaise karein
- Telegram mein apne bot ko `/start` bhejiye
- Koi bhi message likh kar bhejiye, Groq ka jawab aana chahiye
- `/reset` bhejne se conversation history clear ho jayegi

## Zaroori baat — service "so" sakti hai
Render ka free Web Service 15 minute tak koi request na aane par "so" jaata
hai. Isse bachne ke liye, koi free "uptime pinger" (jaise cron-job.org)
istemaal karke har 10 minute mein apne Render URL (jaise
`https://thorai-agent-bot.onrender.com/`) ko ping karwa sakte hain, taaki
bot hamesha jaga rahe.

## Aage kya
Trading module aur automation module jodne ke liye, `webhook()` function
mein message ko check karke decide karenge ki wo trading-related hai ya
general chat — us hisab se sahi module ko call karenge.
