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
social_links = load_json(SOCIAL_FILE, {})

# ================== FLASK ==================
app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'OK', 200

# ================== SEXY ADMIN PANEL ==================
def admin_panel(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("👥 Vendors", callback_data="admin_vendors")
    )
    markup.add(
        types.InlineKeyboardButton("🔗 Social Links", callback_data="admin_social"),
        types.InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
    )
    markup.add(
        types.InlineKeyboardButton("🔄 Refresh Panel", callback_data="admin_refresh")
    )

    text = """🛠️ **Admin Control Panel**
    
Welcome back, Boss! 👑
Choose an option below:"""

    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== START & NORMAL USERS ==================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    subscribers.add(chat_id)
    save_json(SUBSCRIBERS_FILE, list(subscribers))
    
    promo = """Make sure you take 30 seconds out of your time and join us...

This way you’ll never lose us 🔥"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, url in social_links.items():
        markup.add(types.InlineKeyboardButton(name, url=url))
    
    if not social_links:
        markup.add(types.InlineKeyboardButton("Join WhatsApp", url="https://chat.whatsapp.com/YOUR_LINK"))
    
    bot.send_message(chat_id, promo, reply_markup=markup, disable_web_page_preview=True)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin only!")
    admin_panel(message.chat.id)

# ================== CALLBACK HANDLERS (Button Clicks) ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID:
        return bot.answer_callback_query(call.id, "❌ Admin only!", show_alert=True)

    if call.data == "admin_refresh":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        admin_panel(call.message.chat.id)

    elif call.data == "admin_broadcast":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📢 Send your broadcast message now (text only):")
        # Next message will be treated as broadcast

    elif call.data == "admin_vendors":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Vendor", callback_data="add_vendor"))
        markup.add(types.InlineKeyboardButton("➖ Remove Vendor", callback_data="remove_vendor"))
        markup.add(types.InlineKeyboardButton("📋 List Vendors", callback_data="list_vendors"))
        markup.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_refresh"))
        
        text = "👥 **Vendor Management**"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                            reply_markup=markup, parse_mode="Markdown")

    elif call.data == "admin_social":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Social Link", callback_data="add_social"))
        markup.add(types.InlineKeyboardButton("➖ Remove Social", callback_data="remove_social"))
        markup.add(types.InlineKeyboardButton("📋 List Socials", callback_data="list_social"))
        markup.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_refresh"))
        
        text = "🔗 **Social Media Manager**"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                            reply_markup=markup, parse_mode="Markdown")

    elif call.data == "admin_stats":
        bot.answer_callback_query(call.id)
        stats = f"""📊 **Statistics**

Total Subscribers: `{len(subscribers)}`
Active Vendors: `{len(vendors)}`
Social Links: `{len(social_links)}`"""
        bot.send_message(call.message.chat.id, stats, parse_mode="Markdown")

    # Add more sub-handlers later if needed...

# ================== BROADCAST (Next message after button) ==================
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    # Simple broadcast if admin just clicked broadcast button
    if len(subscribers) == 0:
        return bot.reply_to(message, "No subscribers yet.")
    
    sent = 0
    for uid in list(subscribers):
        try:
            bot.send_message(uid, message.text)
            sent += 1
        except:
            subscribers.discard(uid)
    save_json(SUBSCRIBERS_FILE, list(subscribers))
    bot.reply_to(message, f"✅ Broadcast sent to **{sent}** users!")

# ================== START BOT ==================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'your-app.onrender.com')}/{TOKEN}")
    print("🤖 Bot running with Sexy Admin Panel!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
