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

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    channel_id = str(message.channel.id)
    user_message = message.content
    clean = message.clean_content.replace(bot.user.mention, "").strip()
    user_tag = message.author.mention
    user_text = f"{user_tag}: {clean}"

    if channel_id not in chat_sessions:
        chat_sessions[channel_id] = {
            "last_active": time.time(),
            "history": []
        }

    session = chat_sessions[channel_id]

    session["history"].append({"role": "user", "parts": [user_text]})
    session["last_active"] = time.time()
    session["history"] = session["history"][-20:]

    if bot.user.mentioned_in(message):
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(contents=session["history"])
            )
            reply = response.text.strip()

            session["history"].append({"role": "model", "parts": [reply]})
            session["history"] = session["history"][-20:]
            session["last_active"] = time.time()

            clean = message.clean_content.replace(bot.user.mention, "").strip()

            formatted = (
            f"👤 {user_tag} さんが言いました：\n"
            f"＞ *{clean}*\n\n"
            f"🤖 {reply}")

            await message.channel.send(formatted)
        except Exception as e:
            print(f"Error: {e}")
            await message.channel.send("エラーが発生しました。")

@bot.tree.command(name="chat", description="Geminiと会話します")
async def chat_command(interaction: discord.Interaction, *, message: str):
    await interaction.response.defer(thinking=True)
    channel_id = str(interaction.channel.id)
    user_tag = interaction.user.mention
    user_text = f"{user_tag}: {message}"

    try:
        if channel_id not in chat_sessions:
            chat_sessions[channel_id] = {
                "last_active": time.time(),
                "history": []
            }
        
        session = chat_sessions[channel_id]
        history = session["history"] + [
            {"role": "user", "parts": [user_text]}]
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(contents=history)
        )
        reply = response.text.strip()

        session["history"] = history + [{"role": "model", "parts": [reply]}]
        session["history"] = session["history"][-20:]
        session["last_active"] = time.time()

        formatted = (
            f"👤 {interaction.user.mention} さんが言いました：\n"
            f"＞ *{message}*\n\n"
            f"🤖 {reply}"
        )

        await interaction.followup.send(formatted)
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
