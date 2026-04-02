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

# Admin state for button flows
admin_states = {}  # chat_id -> "broadcast" / "add_vendor" / "remove_vendor" etc.

# ================== FLASK WEBHOOK ==================
app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'OK', 200

# ================== SAVE EVERY USER ==================
def save_user(chat_id):
    subscribers.add(chat_id)
    save_json(SUBSCRIBERS_FILE, list(subscribers))

# ================== SEXY ADMIN PANEL ==================
def admin_panel(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("📸 Photo Broadcast", callback_data="admin_photo_broadcast")
    )
    markup.add(
        types.InlineKeyboardButton("👥 Vendors", callback_data="admin_vendors"),
        types.InlineKeyboardButton("🔗 Social Links", callback_data="admin_social")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
        types.InlineKeyboardButton("🧹 Cleanup Dead Users", callback_data="admin_cleanup")
    )
    markup.add(types.InlineKeyboardButton("🔄 Refresh Panel", callback_data="admin_refresh"))

    text = """🛠️ **ADMIN CONTROL PANEL**
👑 Boss Mode Activated

Choose an action below:"""
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== USER START / NORMAL FLOW ==================
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    promo = """Make sure you take 30 seconds out of your time and join us...

This way you’ll never lose us, and you’ll always have access to exclusive content 🔥"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, url in social_links.items():
        markup.add(types.InlineKeyboardButton(name, url=url))
    if not social_links:
        markup.add(types.InlineKeyboardButton("Join WhatsApp", url="https://chat.whatsapp.com/YOUR_LINK_HERE"))
    
    bot.send_message(message.chat.id, promo, reply_markup=markup, disable_web_page_preview=True)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin only!")
    admin_panel(message.chat.id)

# ================== CALLBACK HANDLER (ALL BUTTONS) ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID:
        return bot.answer_callback_query(call.id, "❌ Admin only!", show_alert=True)

    chat_id = call.message.chat.id
    data = call.data

    if data == "admin_refresh":
        bot.delete_message(chat_id, call.message.message_id)
        admin_panel(chat_id)

    elif data == "admin_broadcast":
        bot.answer_callback_query(call.id)
        admin_states[chat_id] = "broadcast"
        bot.send_message(chat_id, "📢 Send the message you want to broadcast:")

    elif data == "admin_photo_broadcast":
        bot.answer_callback_query(call.id)
        admin_states[chat_id] = "photo_broadcast"
        bot.send_message(chat_id, "📸 Send a **photo + caption** (or just text) to broadcast:")

    elif data == "admin_vendors":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Vendor", callback_data="add_vendor"))
        markup.add(types.InlineKeyboardButton("➖ Remove Vendor", callback_data="remove_vendor"))
        markup.add(types.InlineKeyboardButton("📋 List Vendors", callback_data="list_vendors"))
        markup.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_refresh"))
        bot.edit_message_text("👥 **Vendor Management**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "admin_social":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Social", callback_data="add_social"))
        markup.add(types.InlineKeyboardButton("➖ Remove Social", callback_data="remove_social"))
        markup.add(types.InlineKeyboardButton("📋 List Socials", callback_data="list_social"))
        markup.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_refresh"))
        bot.edit_message_text("🔗 **Social Media Manager**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "admin_stats":
        bot.answer_callback_query(call.id)
        stats_text = f"""📊 **Live Statistics**

Total Subscribers: `{len(subscribers)}`
Active Vendors: `{len(vendors)}`
Social Links: `{len(social_links)}`
Bot is running perfectly!"""
        bot.send_message(chat_id, stats_text, parse_mode="Markdown")

    elif data == "admin_cleanup":
        bot.answer_callback_query(call.id)
        removed = 0
        for uid in list(subscribers):
            try:
                bot.send_chat_action(uid, "typing")  # test if user is still reachable
            except:
                subscribers.discard(uid)
                removed += 1
        save_json(SUBSCRIBERS_FILE, list(subscribers))
        bot.send_message(chat_id, f"🧹 Cleaned up **{removed}** dead users!")

    # Sub-actions
    elif data == "add_vendor":
        admin_states[chat_id] = "add_vendor"
        bot.send_message(chat_id, "➕ Send the vendor username (e.g. @dr_razzbhoy1):")
    elif data == "remove_vendor":
        admin_states[chat_id] = "remove_vendor"
        bot.send_message(chat_id, "➖ Send the vendor username to remove:")
    elif data == "list_vendors":
        text = "📋 **Vendors**\n" + "\n".join([f"• {v}" for v in vendors]) if vendors else "No vendors yet."
        bot.send_message(chat_id, text)
    elif data == "add_social":
        admin_states[chat_id] = "add_social"
        bot.send_message(chat_id, "➕ Send in format: Name https://link.com")
    elif data == "remove_social":
        admin_states[chat_id] = "remove_social"
        bot.send_message(chat_id, "➖ Send the exact name of the social link to remove:")
    elif data == "list_social":
        if not social_links:
            bot.send_message(chat_id, "No social links yet.")
            return
        text = "🔗 **Social Links**\n\n"
        for name, url in social_links.items():
            text += f"• **{name}**: {url}\n"
        bot.send_message(chat_id, text, disable_web_page_preview=True)

# ================== HANDLE ADMIN INPUTS ==================
@bot.message_handler(func=lambda m: True)
def handle_admin_input(message):
    if message.from_user.id != ADMIN_ID:
        save_user(message.chat.id)  # save every normal user too
        return

    chat_id = message.chat.id
    state = admin_states.get(chat_id)

    if not state:
        save_user(chat_id)
        return

    # Broadcast text
    if state == "broadcast":
        sent = 0
        for uid in list(subscribers):
            try:
                bot.send_message(uid, message.text)
                sent += 1
            except:
                subscribers.discard(uid)
        save_json(SUBSCRIBERS_FILE, list(subscribers))
        bot.reply_to(message, f"✅ Broadcast sent to **{sent}** users!")
        admin_states.pop(chat_id, None)

    # Photo + caption broadcast
    elif state == "photo_broadcast":
        sent = 0
        for uid in list(subscribers):
            try:
                if message.photo:
                    bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption or "")
                else:
                    bot.send_message(uid, message.text)
                sent += 1
            except:
                subscribers.discard(uid)
        save_json(SUBSCRIBERS_FILE, list(subscribers))
        bot.reply_to(message, f"✅ Photo/Text broadcast sent to **{sent}** users!")
        admin_states.pop(chat_id, None)

    # Add vendor
    elif state == "add_vendor":
        username = message.text.strip()
        if username not in vendors:
            vendors.append(username)
            save_json(VENDORS_FILE, vendors)
            bot.reply_to(message, f"✅ Added: {username}")
        else:
            bot.reply_to(message, "⚠️ Already exists")
        admin_states.pop(chat_id, None)

    # Remove vendor
    elif state == "remove_vendor":
        username = message.text.strip()
        if username in vendors:
            vendors.remove(username)
            save_json(VENDORS_FILE, vendors)
            bot.reply_to(message, f"✅ Removed: {username}")
        else:
            bot.reply_to(message, "⚠️ Not found")
        admin_states.pop(chat_id, None)

    # Add social
    elif state == "add_social":
        try:
            parts = message.text.split(maxsplit=1)
            name = parts[0]
            url = parts[1]
            social_links[name] = url
            save_json(SOCIAL_FILE, social_links)
            bot.reply_to(message, f"✅ Added social: **{name}**")
        except:
            bot.reply_to(message, "Format: Name https://link.com")
        admin_states.pop(chat_id, None)

    # Remove social
    elif state == "remove_social":
        name = message.text.strip()
        if name in social_links:
            del social_links[name]
            save_json(SOCIAL_FILE, social_links)
            bot.reply_to(message, f"✅ Removed: {name}")
        else:
            bot.reply_to(message, "⚠️ Not found")
        admin_states.pop(chat_id, None)

# ================== START BOT ==================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'your-app.onrender.com')}/{TOKEN}")
    print("🤖 Bot running with FULLY FUNCTIONAL Sexy Admin Panel + Advanced Features!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
