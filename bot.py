import telebot
import os
import json
from flask import Flask, request
from telebot import types

# ================== CONFIG ==================
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 123456789))

bot = telebot.TeleBot(TOKEN)

# Files
SUBSCRIBERS_FILE = "subscribers.json"
VENDORS_FILE = "vendors.json"
SOCIAL_FILE = "social_links.json"

def load_json(file, default=[]):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

subscribers = set(load_json(SUBSCRIBERS_FILE))
vendors = load_json(VENDORS_FILE)
social_links = load_json(SOCIAL_FILE, {})   # Example: {"WhatsApp": "https://...", "Instagram": "https://..."}

# ================== FLASK WEBHOOK ==================
app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
    return 'OK', 200

# ================== SEXY START MESSAGE ==================
def send_sexy_start(chat_id):
    promo_text = """Make sure you take 30 seconds out of your time and join us...

This way you’ll never lose us, and you’ll always have access to exclusive content 🔥

Click the buttons below 👇"""

    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for name, url in social_links.items():
        markup.add(types.InlineKeyboardButton(name, url=url))
    
    # Fallback if no links added
    if not social_links:
        markup.add(types.InlineKeyboardButton("Join WhatsApp", url="https://chat.whatsapp.com/YOUR_LINK"))
    
    bot.send_message(chat_id, promo_text, reply_markup=markup, disable_web_page_preview=True)

# ================== COMMANDS ==================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    subscribers.add(chat_id)
    save_json(SUBSCRIBERS_FILE, list(subscribers))
    
    send_sexy_start(chat_id)
    bot.send_message(chat_id, "✅ You're now subscribed for broadcasts!")

# Broadcast
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
                subscribers.discard(uid)
        save_json(SUBSCRIBERS_FILE, list(subscribers))
        bot.reply_to(message, f"✅ Sent to {sent} users!")
    except:
        bot.reply_to(message, "Usage: /broadcast Your message")

# === Vendor Management ===
@bot.message_handler(commands=['addvendor'])
def add_vendor(message):
    if message.from_user.id != ADMIN_ID: return bot.reply_to(message, "❌ Admin only!")
    try:
        username = message.text.split(maxsplit=1)[1].strip()
        if username not in vendors:
            vendors.append(username)
            save_json(VENDORS_FILE, vendors)
            bot.reply_to(message, f"✅ Added vendor: {username}")
        else:
            bot.reply_to(message, "⚠️ Already exists")
    except:
        bot.reply_to(message, "Usage: /addvendor @username")

@bot.message_handler(commands=['removevendor'])
def remove_vendor(message):
    if message.from_user.id != ADMIN_ID: return bot.reply_to(message, "❌ Admin only!")
    try:
        username = message.text.split(maxsplit=1)[1].strip()
        if username in vendors:
            vendors.remove(username)
            save_json(VENDORS_FILE, vendors)
            bot.reply_to(message, f"✅ Removed: {username}")
    except:
        bot.reply_to(message, "Usage: /removevendor @username")

@bot.message_handler(commands=['vendors'])
def list_vendors(message):
    if message.from_user.id != ADMIN_ID: return bot.reply_to(message, "❌ Admin only!")
    text = "📋 **Vendors**\n" + "\n".join([f"• {v}" for v in vendors]) if vendors else "No vendors yet."
    bot.reply_to(message, text, parse_mode="Markdown")

# === SOCIAL MEDIA MANAGEMENT (New Feature) ===
@bot.message_handler(commands=['addsocial'])
def add_social(message):
    if message.from_user.id != ADMIN_ID: return bot.reply_to(message, "❌ Admin only!")
    try:
        parts = message.text.split(maxsplit=2)
        name = parts[1].strip()
        url = parts[2].strip()
        social_links[name] = url
        save_json(SOCIAL_FILE, social_links)
        bot.reply_to(message, f"✅ Added social: **{name}** → {url}", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Usage: /addsocial Name https://link.com")

@bot.message_handler(commands=['removesocial'])
def remove_social(message):
    if message.from_user.id != ADMIN_ID: return bot.reply_to(message, "❌ Admin only!")
    try:
        name = message.text.split(maxsplit=1)[1].strip()
        if name in social_links:
            del social_links[name]
            save_json(SOCIAL_FILE, social_links)
            bot.reply_to(message, f"✅ Removed social: {name}")
        else:
            bot.reply_to(message, "⚠️ Not found")
    except:
        bot.reply_to(message, "Usage: /removesocial Name")

@bot.message_handler(commands=['socials', 'listsocial'])
def list_social(message):
    if message.from_user.id != ADMIN_ID: return bot.reply_to(message, "❌ Admin only!")
    if not social_links:
        return bot.reply_to(message, "No social links yet. Add with /addsocial")
    text = "🔗 **Social Media Links**\n\n"
    for name, url in social_links.items():
        text += f"• **{name}**: {url}\n"
    bot.reply_to(message, text, parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=['id'])
def get_id(message):
    bot.reply_to(message, f"Your ID: `{message.from_user.id}`", parse_mode="Markdown")

# ================== START ==================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'your-app.onrender.com')}/{TOKEN}")
    print("🤖 Bot started with webhook + Social Media Manager!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
