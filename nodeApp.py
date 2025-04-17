import json
import random
import time
import threading
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

with open("question.json", "r") as f:
    questions = json.load(f)

def load_data():
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

user_data = load_data()
running_users = {}

def send_chat_request(api_key, question):
    data = {
        "messages": [{"role": "user", "content": question}],
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 0.9
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.post("https://api.hyperbolic.xyz/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except:
        return None

def node_runner(user_id, context):
    stats = running_users[user_id]
    while stats['running']:
        question = random.choice(questions)
        send_chat_request(stats['key'], question)  # response not shown
        stats['count'] += 1
        time.sleep(stats['gap'])

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
Commands:
/node_key <API Key> - Set your Hyperbolic API key
/node run - Start your AI node
/node stop - Stop your node
/node stats - Show your current session stats
/node gap <seconds> - Set gap between requests (10-60 seconds)
/help - Show this message
    """
    await update.message.reply_text(msg)

async def node_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /node_key <API Key>")
        return
    key = context.args[0]
    user_data[user_id] = key
    save_data(user_data)
    await update.message.reply_text("API Key saved successfully!")

async def node_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("You need to setup your Hyperbolic AI node API Key to run the node!")
        return
    if user_id in running_users and running_users[user_id]['running']:
        await update.message.reply_text("Your node is already running!")
        return
    running_users[user_id] = {
        "key": user_data[user_id],
        "count": 0,
        "start": time.ctime(),
        "gap": 20,
        "running": True
    }
    threading.Thread(target=node_runner, args=(user_id, context), daemon=True).start()
    await update.message.reply_text("Your AI node has started!")

async def node_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in running_users:
        running_users[user_id]['running'] = False
        await update.message.reply_text("Your AI node has stopped.")
    else:
        await update.message.reply_text("Your node is not running.")

async def node_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in running_users:
        stats = running_users[user_id]
        msg = f"""
Telegram UID: {user_id}
Question number: {stats['count']}
Starting time: {stats['start']}
Gap: {stats['gap']} seconds
Running: {stats['running']}
        """
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("Node not running or stats unavailable.")

async def node_gap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in running_users:
        await update.message.reply_text("Start the node first using /node run")
        return
    if not context.args:
        await update.message.reply_text("Usage: /node gap <seconds>")
        return
    try:
        gap = int(context.args[0])
        if 10 <= gap <= 60:
            running_users[user_id]['gap'] = gap
            await update.message.reply_text(f"Gap updated to {gap} seconds.")
        else:
            await update.message.reply_text("Gap must be between 10 and 60 seconds.")
    except:
        await update.message.reply_text("Invalid number. Usage: /node gap <seconds>")

def main():
    app = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("node_key", node_key))
    app.add_handler(CommandHandler("node", node_run, block=False))
    app.add_handler(CommandHandler("node", node_stop, filters=None, block=False))
    app.add_handler(CommandHandler("node", node_stats, filters=None, block=False))
    app.add_handler(CommandHandler("node", node_gap, filters=None, block=False))
    app.run_polling()

if __name__ == "__main__":
    main()
