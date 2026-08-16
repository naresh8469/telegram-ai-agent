Telegram AI Agent Bot — Render Free Web Service Deployment Guide
Kya hai ye
Ye ek Telegram bot hai jo Google Gemini AI se connect hai. Ye "Web Service"
ki tarah chalta hai (free, card nahi chahiye) aur Telegram se "webhook" ke
zariye messages receive karta hai.

Gemini API Key kaise banayein
aistudio.google.com kholiye aur apne Google account se login kijiye
Get API Key par click kijiye
Create API Key dabaiye — koi card ki zaroorat nahi
Key ko copy karke rakh lijiye
Render pe Deploy karne ke steps
Render dashboard kholiye, New + → Web Service chuniye
(Background Worker NAHI — Web Service, jisme free option hai)

Apna GitHub repo connect kijiye jisme ye teen files hain (bot.py,
requirements.txt, README.md)

Settings:

Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn bot:app
Instance Type: Free
Environment Variables mein add kijiye:

TELEGRAM_BOT_TOKEN = BotFather se mila token
GEMINI_API_KEY = aapki Gemini API key
Create Web Service dabaiye — deploy hone do

Deploy poora hone ke baad, Render aapko ek URL dega, jaise:
https://thorai-agent-bot.onrender.com
Ise copy kar lijiye.

Webhook set karna (ek baar ka kaam)
Deploy hone ke baad, apna bot Telegram se connect karne ke liye webhook set
karna hoga. Apne phone ke browser mein ye URL kholiye (apna token aur
Render URL daal kar):

https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<aapka-render-url>.onrender.com/webhook/<TELEGRAM_BOT_TOKEN>
Jaise agar token 123:ABC hai aur Render URL thorai-agent-bot.onrender.com
hai, to:

https://api.telegram.org/bot123:ABC/setWebhook?url=https://thorai-agent-bot.onrender.com/webhook/123:ABC
Browser mein {"ok":true,"result":true,...} dikhna chahiye — iska matlab
webhook set ho gaya.

Test kaise karein
Telegram mein apne bot ko /start bhejiye
Koi bhi message likh kar bhejiye, Gemini ka jawab aana chahiye
/reset bhejne se conversation history clear ho jayegi
Zaroori baat — service "so" sakti hai
Render ka free Web Service 15 minute tak koi request na aane par "so" jaata
hai. Isse bachne ke liye, koi free "uptime pinger" (jaise cron-job.org)
istemaal karke har 10 minute mein apne Render URL (jaise
https://thorai-agent-bot.onrender.com/) ko ping karwa sakte hain, taaki
bot hamesha jaga rahe.

Aage kya
Trading module aur automation module jodne ke liye, webhook() function
mein message ko check karke decide karenge ki wo trading-related hai ya
general chat — us hisab se sahi module ko call karenge.
