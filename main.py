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

@discord_client.event
async def on_ready():
    print(f'Logged in as {discord_client.user}')

@discord_client.event
async def on_message(message):
    if message.author.bot:
        return

    if "#要約" in message.content:
        original = message.content.replace("#要約", "").strip()
        prompt = f"以下の文章を日本語で簡潔に要約してください：\n{original}"

        try:
            response = chat.send_message(prompt)
            summary = response.text.strip()
            await message.channel.send(f"📝 要約:\n{summary}")
        except Exception as e:
            await message.channel.send(f"エラーが発生しました: {str(e)}")

discord_client.run(DISCORD_TOKEN)
