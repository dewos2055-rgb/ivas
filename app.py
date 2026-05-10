import os
import threading
from flask import Flask
from telegram import Bot
from telegram.ext import Application, CommandHandler

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# FLASK
# =========================

@app.route("/")
def home():
    return "BOT RUNNING"

# =========================
# TELEGRAM BOT
# =========================

async def start(update, context):
    await update.message.reply_text(
        "Bot aktif"
    )

async def otp(update, context):

    # simulasi OTP
    otp_code = "123456"

    await update.message.reply_text(
        f"OTP: {otp_code}"
    )

def run_bot():

    application = Application.builder().token(
        BOT_TOKEN
    ).build()

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("otp", otp)
    )

    application.run_polling()

# =========================
# MAIN
# =========================

if __name__ == "__main__":

    bot_thread = threading.Thread(
        target=run_bot
    )

    bot_thread.start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
