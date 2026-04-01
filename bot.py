import telebot
import os
import json
from flask import Flask, request

# ================== CONFIG ==================
TOKEN = os.environ.get("8669926146:AAGqK0YGZ0YcVq9KocoKOYwYSrKSI0koofQ")                    # Set in Render/Railway
ADMIN_ID = int(os.environ.get("ADMIN_ID", 7755445436))  # Your Telegram ID

bot = telebot.TeleBot(TOKEN)

SUBSCRIBERS_FILE = "subscribers.json"
VENDORS_FILE = "vendors.json"

# Load / Save helpers
def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return [] if "vendors" in file else []

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

subscribers = set(load_json(SUBSCRIBERS_FILE))
vendors = load_json(VENDORS_FILE)

# Promotional message (adapted from your screenshot)
PROMO_MESSAGE = """Make sure you take 30 seconds out of your time and join the WhatsApp...
this way you’ll never lose us, and you’ll always have access to the exclusive content I put out...

I know so many of you rely on me and have done in the past, just by clicking that button, you might save yourself future hassle 🤙🇬🇧

https://chat.whatsapp.com/YOUR_LINK_HERE   ← Replace with your real link"""

# Flask App for Webhook
app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
    return 'OK', 200

# ================== BOT COMMANDS ==================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    subscribers.add(chat_id)
    save_json(SUBSCRIBERS_FILE, list(subscribers))
    
    bot.reply_to(message, PROMO_MESSAGE)
    bot.send_message(chat_id, "✅ You're now subscribed! I'll send you broadcasts.")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin only!")
    
    try:
        text = message.text.split(maxsplit=1)[1]
        sent = 0
        for uid in list(subscribers):
            try:
                bot.send_message(uid, text)
                sent += 1
            except:
                subscribers.discard(uid)  # Remove dead users
        save_json(SUBSCRIBERS_FILE, list(subscribers))
        bot.reply_to(message, f"✅ Broadcast sent to {sent} users!")
    except:
        bot.reply_to(message, "Usage: /broadcast Your message here")

@bot.message_handler(commands=['addvendor'])
def add_vendor(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin only!")
    try:
        username = message.text.split(maxsplit=1)[1].strip()
        if username not in vendors:
            vendors.append(username)
            save_json(VENDORS_FILE, vendors)
            bot.reply_to(message, f"✅ Added: {username}")
        else:
            bot.reply_to(message, "⚠️ Already in list")
    except:
        bot.reply_to(message, "Usage: /addvendor @username")

@bot.message_handler(commands=['removevendor'])
def remove_vendor(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin only!")
    try:
        username = message.text.split(maxsplit=1)[1].strip()
        if username in vendors:
            vendors.remove(username)
            save_json(VENDORS_FILE, vendors)
            bot.reply_to(message, f"✅ Removed: {username}")
        else:
            bot.reply_to(message, "⚠️ Not found")
    except:
        bot.reply_to(message, "Usage: /removevendor @username")

@bot.message_handler(commands=['vendors', 'listvendors'])
def list_vendors(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin only!")
    if not vendors:
        return bot.reply_to(message, "No vendors yet.")
    text = "📋 **Vendor Management**\n\n" + "\n".join([f"• {v}" for v in vendors])
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def get_id(message):
    bot.reply_to(message, f"Your ID: `{message.from_user.id}`", parse_mode="Markdown")

# ================== START BOT ==================
if __name__ == "__main__":
    # Remove old webhook and set new one
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'your-app.onrender.com')}/{TOKEN}")
    
    print("🤖 Bot started with webhook!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
