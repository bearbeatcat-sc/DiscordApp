import os
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import discord
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
bot = commands.Bot(command_prefix="!", intents=intents)

chat_sessions = {}

def cleanup_inactive_sessions(timeout_seconds=3600):
    now = time.time()
    inactive_channels = [
        channel_id for channel_id, session in chat_sessions.items()
        if now - session["last_active"] > timeout_seconds
    ]
    for channel_id in inactive_channels:
        del chat_sessions[channel_id]
        print(f"🧹 Removed inactive session for channel: {channel_id}")

# バックグラウンドタスクで定期的にセッションをクリーンアップ
async def session_cleanup_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        cleanup_inactive_sessions(timeout_seconds=3600)
        await asyncio.sleep(600)  # 10分ごとに実行

@bot.tree.command(name="chat", description="Geminiと会話します")
async def chat_command(interaction: discord.Interaction, *, message: str):
    await interaction.response.defer(thinking=True)
    channel_id = str(interaction.channel.id)

    try:
        if channel_id not in chat_sessions:
            chat_sessions[channel_id] = {
                "chat": model.start_chat(),
                "last_active": time.time()
            }
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, chat_sessions[channel_id]["chat"].send_message, message)
        reply = response.text.strip()

        chat_sessions[channel_id]['last_active'] = time.time()
        await interaction.followup.send(reply)
    except Exception as e:
        print(f"Error: {e}")
        await interaction.followup.send("エラーが発生しました。")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")
    if not hasattr(bot, 'cleanup_task') or bot.cleanup_task.done():
        bot.cleanup_task = bot.loop.create_task(session_cleanup_loop())

@bot.tree.command(name="clear", description="セッションをクリアします")
async def clear_command(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    if channel_id in chat_sessions:
        del chat_sessions[channel_id]
        await interaction.response.send_message("セッションをクリアしました。")
    else:
        await interaction.response.send_message("セッションは存在しません。")

bot.run(DISCORD_TOKEN)
