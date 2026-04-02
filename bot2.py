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
WELCOME_FILE = "welcome_message.json"

def load_json(file, default=[]):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if isinstance(default, list) else default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

subscribers = set(load_json(SUBSCRIBERS_FILE))
vendors = load_json(VENDORS_FILE)
social_links = load_json(SOCIAL_FILE, {})
welcome_message = load_json(WELCOME_FILE, """Make sure you take 30 seconds out of your time and join us...

This way you’ll never lose us, and you’ll always have access to exclusive content 🔥""")

# Admin state
admin_states = {}  # chat_id -> action

# ================== FLASK WEBHOOK ==================
app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'OK', 200

# Save every user who interacts
def save_user(chat_id):
    subscribers.add(chat_id)
    save_json(SUBSCRIBERS_FILE, list(subscribers))

# ================== ADMIN PANEL ==================
def admin_panel(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Text Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("📰 News Post", callback_data="admin_news")
    )
    markup.add(
        types.InlineKeyboardButton("✏️ Edit Welcome", callback_data="admin_edit_welcome"),
        types.InlineKeyboardButton("👥 Vendors", callback_data="admin_vendors")
    )
    markup.add(
        types.InlineKeyboardButton("🔗 Social Links", callback_data="admin_social"),
        types.InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
    )
    markup.add(
        types.InlineKeyboardButton("📤 Export Users", callback_data="admin_export"),
        types.InlineKeyboardButton("🧹 Cleanup Dead", callback_data="admin_cleanup")
    )
    markup.add(
        types.InlineKeyboardButton("🗑️ Clear All Users", callback_data="admin_clear_confirm"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")
    )

    text = """🛠️ **ADMIN CONTROL PANEL** 👑

Choose any option below:"""
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== WELCOME MESSAGE ==================
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, url in social_links.items():
        markup.add(types.InlineKeyboardButton(name, url=url))
    if not social_links:
        markup.add(types.InlineKeyboardButton("Join WhatsApp", url="https://chat.whatsapp.com/YOUR_LINK_HERE"))
    
    bot.send_message(message.chat.id, welcome_message, reply_markup=markup, disable_web_page_preview=True)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin only!")
    admin_panel(message.chat.id)

# ================== CALLBACK HANDLER ==================
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
        admin_states[chat_id] = "broadcast"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📢 Send your text broadcast:")

    elif data == "admin_news":
        admin_states[chat_id] = "news"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📰 Send News Post (photo + caption or text only):")

    elif data == "admin_edit_welcome":
        admin_states[chat_id] = "edit_welcome"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"✏️ Current welcome:\n\n{welcome_message}\n\nSend the new welcome message:")

    elif data == "admin_vendors":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Vendor", callback_data="add_vendor"))
        markup.add(types.InlineKeyboardButton("➖ Remove Vendor", callback_data="remove_vendor"))
        markup.add(types.InlineKeyboardButton("📋 List Vendors", callback_data="list_vendors"))
        markup.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_refresh"))
        bot.edit_message_text("👥 **Vendor Management**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "admin_social":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Social", callback_data="add_social"))
        markup.add(types.InlineKeyboardButton("➖ Remove Social", callback_data="remove_social"))
        markup.add(types.InlineKeyboardButton("📋 List Socials", callback_data="list_social"))
        markup.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_refresh"))
        bot.edit_message_text("🔗 **Social Media Manager**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "admin_stats":
        bot.answer_callback_query(call.id)
        text = f"""📊 **Statistics**

Total Subscribers: `{len(subscribers)}`
Vendors: `{len(vendors)}`
Social Links: `{len(social_links)}`"""
        bot.send_message(chat_id, text, parse_mode="Markdown")

    elif data == "admin_export":
        bot.answer_callback_query(call.id)
        if subscribers:
            with open("subscribers.txt", "w") as f:
                f.write("\n".join(str(uid) for uid in subscribers))
            with open("subscribers.txt", "rb") as f:
                bot.send_document(chat_id, f, caption="📤 All subscriber IDs")
            os.remove("subscribers.txt")
        else:
            bot.send_message(chat_id, "No subscribers yet.")

    elif data == "admin_cleanup":
        bot.answer_callback_query(call.id)
        removed = 0
        for uid in list(subscribers):
            try:
                bot.send_chat_action(uid, "typing")
            except:
                subscribers.discard(uid)
                removed += 1
        save_json(SUBSCRIBERS_FILE, list(subscribers))
        bot.send_message(chat_id, f"🧹 Removed **{removed}** dead users!")

    elif data == "admin_clear_confirm":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ YES, CLEAR ALL", callback_data="admin_clear_yes"))
        markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="admin_refresh"))
        bot.send_message(chat_id, "⚠️ Delete ALL subscribers permanently?", reply_markup=markup)

    elif data == "admin_clear_yes":
        subscribers.clear()
        save_json(SUBSCRIBERS_FILE, [])
        bot.answer_callback_query(call.id, "Cleared!", show_alert=True)
        bot.send_message(chat_id, "🗑️ All subscribers cleared.")

    # Sub actions
    elif data.startswith("add_") or data.startswith("remove_") or data == "list_vendors" or data == "list_social":
        if data == "add_vendor":
            admin_states[chat_id] = "add_vendor"
            bot.send_message(chat_id, "➕ Send vendor username (@username):")
        elif data == "remove_vendor":
            admin_states[chat_id] = "remove_vendor"
            bot.send_message(chat_id, "➖ Send vendor username to remove:")
        elif data == "list_vendors":
            text = "📋 **Vendors**\n" + "\n".join(f"• {v}" for v in vendors) if vendors else "No vendors."
            bot.send_message(chat_id, text)
        elif data == "add_social":
            admin_states[chat_id] = "add_social"
            bot.send_message(chat_id, "➕ Send: Name https://link.com")
        elif data == "remove_social":
            admin_states[chat_id] = "remove_social"
            bot.send_message(chat_id, "➖ Send exact social name to remove:")
        elif data == "list_social":
            if not social_links:
                bot.send_message(chat_id, "No social links.")
                return
            text = "🔗 **Social Links**\n\n" + "\n".join(f"• **{name}**: {url}" for name, url in social_links.items())
            bot.send_message(chat_id, text, disable_web_page_preview=True)

# ================== HANDLE ADMIN TEXT INPUT ==================
@bot.message_handler(func=lambda m: True)
def handle_input(message):
    if message.from_user.id != ADMIN_ID:
        save_user(message.chat.id)
        return

    chat_id = message.chat.id
    state = admin_states.get(chat_id)
    if not state:
        save_user(chat_id)
        return

    # Text Broadcast
    if state == "broadcast":
        sent = 0
        for uid in list(subscribers):
            try:
                bot.send_message(uid, message.text)
                sent += 1
            except:
                subscribers.discard(uid)
        save_json(SUBSCRIBERS_FILE, list(subscribers))
        bot.reply_to(message, f"✅ Sent to **{sent}** users!")
        admin_states.pop(chat_id, None)

    # News Post
    elif state == "news":
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
        bot.reply_to(message, f"📰 News sent to **{sent}** users!")
        admin_states.pop(chat_id, None)

    # Edit Welcome
    elif state == "edit_welcome":
        global welcome_message
        welcome_message = message.text
        save_json(WELCOME_FILE, welcome_message)
        bot.reply_to(message, "✅ Welcome message updated!")
        admin_states.pop(chat_id, None)

    # Vendors
    elif state == "add_vendor":
        username = message.text.strip()
        if username not in vendors:
            vendors.append(username)
            save_json(VENDORS_FILE, vendors)
            bot.reply_to(message, f"✅ Added {username}")
        admin_states.pop(chat_id, None)

    elif state == "remove_vendor":
        username = message.text.strip()
        if username in vendors:
            vendors.remove(username)
            save_json(VENDORS_FILE, vendors)
            bot.reply_to(message, f"✅ Removed {username}")
        admin_states.pop(chat_id, None)

    # Social
    elif state == "add_social":
        try:
            parts = message.text.split(maxsplit=1)
            name = parts[0]
            url = parts[1]
            social_links[name] = url
            save_json(SOCIAL_FILE, social_links)
            bot.reply_to(message, f"✅ Added {name}")
        except:
            bot.reply_to(message, "Format: Name https://link.com")
        admin_states.pop(chat_id, None)

    elif state == "remove_social":
        name = message.text.strip()
        if name in social_links:
            del social_links[name]
            save_json(SOCIAL_FILE, social_links)
            bot.reply_to(message, f"✅ Removed {name}")
        admin_states.pop(chat_id, None)

# ================== START BOT ==================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'your-app.onrender.com')}/{TOKEN}")
    print("🤖 Bot fully ready with advanced admin panel!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
