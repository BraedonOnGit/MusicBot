import os
import random
import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Dictionary to keep track of voice clients and queues
voice_clients = {}
music_queues = {}

# Specify the allowed channel name
ALLOWED_CHANNEL = "music-bot"
BRASS_MONKEY_URL = "https://www.youtube.com/watch?v=acY2VSskD80"

# Load environment variables from .env file
load_dotenv()

# Get the bot token from the .env file
TOKEN = os.getenv("DISCORD_BOT_TOKEN")



@bot.event
async def on_ready():
    print(f"Logged on as {bot.user}!")

# Helper function to check if the command is in the allowed channel
async def is_allowed_channel(ctx):
    if ctx.channel.name != ALLOWED_CHANNEL:
        await ctx.send(f"```\nCommands are only allowed in the #{ALLOWED_CHANNEL} channel.\n```")
        return False
    return True

# Function to play the next song in the queue
async def play_next(ctx, guild_id):
    if music_queues[guild_id]:
        next_url = music_queues[guild_id].pop(0)
        await play_song(ctx, guild_id, next_url)
    else:
        await ctx.send("```\nQueue is empty.\n```")

# Function to play a song
# Function to play a song
async def play_song(ctx, guild_id, url):
    voice_client = voice_clients[guild_id]
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            source = await discord.FFmpegOpusAudio.from_probe(url2)

            def after_playing(error):
                if error:
                    print(f"Error occurred: {error}")
                asyncio.run_coroutine_threadsafe(play_next(ctx, guild_id), bot.loop)

            voice_client.play(source, after=after_playing)

        # Include the original YouTube URL in the response
        await ctx.send(
            f"```\nNow playing: {info['title']}\nLink: {info['webpage_url']}\n```"
        )
    except Exception as e:
        await ctx.send(f"```\nAn error occurred: {e}\n```")

# Command to join a voice channel
@bot.command()
async def join(ctx):
    if not await is_allowed_channel(ctx):
        return

    if ctx.author.voice:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()
        voice_clients[ctx.guild.id] = voice_client
        music_queues[ctx.guild.id] = []  # Initialize the queue for this guild
        await ctx.send(f"```\nJoined {channel}!\n```")
    else:
        await ctx.send("```\nYou need to join a voice channel first!\n```")

# Command to leave a voice channel
@bot.command()
async def leave(ctx):
    if not await is_allowed_channel(ctx):
        return

    if ctx.guild.id in voice_clients:
        await voice_clients[ctx.guild.id].disconnect()
        del voice_clients[ctx.guild.id]
        music_queues.pop(ctx.guild.id, None)  # Clear the queue
        await ctx.send("```\nDisconnected!\n```")
    else:
        await ctx.send("```\nI'm not in a voice channel!\n```")

# Command to play music
@bot.command()
async def play(ctx, *, query):
    if not await is_allowed_channel(ctx):
        return

    guild_id = ctx.guild.id
    if guild_id not in voice_clients:
        await ctx.send("```\nI'm not in a voice channel! Use the `!join` command first.\n```")
        return

    # 1/20 chance to override the song with "Brass Monkey"
    if random.randint(1, 20) == 1:
        query = BRASS_MONKEY_URL
        await ctx.send("```\nOh I'm sorry but I really wanted to play Brass Monkey?\n```")

    # If query is a URL, play it directly; otherwise, search for the query on YouTube
    if not query.startswith("http"):
        await ctx.send(f"```\nSearching for '{query}' on YouTube...\n```")
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'default_search': 'ytsearch',  # Search on YouTube
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                query = info['entries'][0]['webpage_url']  # Get the first result URL
                await ctx.send(f"```\nFound: {info['entries'][0]['title']}\n```")
        except Exception as e:
            await ctx.send(f"```\nAn error occurred while searching: {e}\n```")
            return

    if voice_clients[guild_id].is_playing():
        # Add the song to the queue
        music_queues[guild_id].append(query)
        await ctx.send("```\nAdded to the queue!\n```")
    else:
        # Play the song immediately
        await play_song(ctx, guild_id, query)

# Command to stop music
@bot.command()
async def stop(ctx):
    if not await is_allowed_channel(ctx):
        return

    if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
        voice_clients[ctx.guild.id].stop()
        music_queues[ctx.guild.id].clear()  # Clear the queue
        await ctx.send("```\nPlayback stopped and queue cleared!\n```")
    else:
        await ctx.send("```\nNo music is currently playing!\n```")

# Command to skip to the next song
@bot.command()
async def skip(ctx):
    if not await is_allowed_channel(ctx):
        return

    guild_id = ctx.guild.id
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        # Stop the current song, and the `after` callback will handle playing the next one
        voice_clients[guild_id].stop()
        await ctx.send("```\nSkipped to the next song!\n```")
    else:
        await ctx.send("```\nNo music is currently playing!\n```")

# Command to display help
@bot.command()
async def help(ctx):
    help_message = """
    Music Bot Commands:
    - !join: Makes the bot join your current voice channel.
    - !leave: Makes the bot leave the current voice channel.
    - !play <url or song name>: Plays a song from YouTube. If a song name is provided, it searches and plays the first result.
    - !stop: Stops the current playback and clears the queue.
    - !skip: Skips the current song and plays the next one in the queue.
    - !help: Displays this list of commands and their descriptions.

    Note: Commands can only be used in the #music-bot channel.
    [Link to Repository](https://github.com/BraedonOnGit/MusicBot)
    """
    await ctx.send(help_message)

# Run the bot
bot.run(TOKEN)
