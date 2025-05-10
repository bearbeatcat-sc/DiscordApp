import os
import discord
from dotenv import load_dotenv
import google.generativeai as genai

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

@discord_client.event
async def on_ready():
    print(f'Logged in as {discord_client.user}')

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
            chat_sessions[user_id] = model.start_chat()
            response = chat_sessions[user_id].send_message(user_message)

            reply = response.text.strip()
            await message.channel.send(reply)
    except Exception as e:
        print(f"Error: {e}")
        await message.channel.send("An error occurred while processing your request.")
        
discord_client.run(DISCORD_TOKEN)
