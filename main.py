import os
import discord
from dotenv import load_dotenv
import google.generativeai as genai
import time
import asyncio

# 環境変数からAPIキー取得
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-2.5-flash-preview-04-17")
chat = model.start_chat()

# Discord Bot設定
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

chat_sessions = {}

def cleanup_inactive_sessions(timeout_seconds=3600):
    now = time.time()
    inactive_users = [
        user_id for user_id, sessions in chat_sessions.items()
        if now - sessions['last_active'] > timeout_seconds
    ]

    for user_id in inactive_users:
        del chat_sessions[user_id]

async def session_cleanup_loop():
    await discord_client.wait_until_ready()
    while not discord_client.is_closed():
        cleanup_inactive_sessions(timeout_seconds=3600)  # 1時間以上非アクティブなセッションを削除
        await asyncio.sleep(600)  # 10分ごとにチェック

@discord_client.event
async def on_ready():
    print(f'Logged in as {discord_client.user}')
    discord_client.loop.create_task(session_cleanup_loop())

@discord_client.event
async def on_message(message):
    if message.author.bot:
        return
    
    user_id = str(message.author.id)
    user_message = message.content.strip()
    
    if not user_message:
        return
    
    try:
        if user_id not in chat_sessions:
            chat_sessions[user_id] = {
                "chat": model.start_chat(),
                "last_active": time.time()
            }
        
        response = chat_sessions[user_id]["chat"].send_message(user_message)
        reply = response.text.strip()
        chat_sessions[user_id]['last_active'] = time.time()
        await message.channel.send(reply)
        
    except Exception as e:
        print(f"Error: {e}")
        await message.channel.send("An error occurred while processing your request.")
        
discord_client.run(DISCORD_TOKEN)
