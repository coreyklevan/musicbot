import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import time
import urllib.parse, urllib.request, re

def run_bot():
    load_dotenv()
    TOKEN = ("MTE1NTg0NjY5NDgwNjc2OTczNg.Gzxo1y.VPuw91vO6u11j_ZJC1DVV0wM_1xOH2rIK6aQAA")    
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix="!", intents=intents)

    queues = {}
    voice_clients = {}
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

    volume_levels = {}  # Store volume levels per guild

    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming')

    async def play_next(ctx):
        guild_id = ctx.guild.id

        if guild_id in queues and queues[guild_id]:  # Check if queue exists and isn't empty
            next_song = queues[guild_id].pop(0)

            try:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(next_song['url'], download=False))
                song_url = data['url']
                player = discord.FFmpegOpusAudio(song_url, **ffmpeg_options)

                voice_clients[guild_id].play(
                    player, 
                    after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop)
                )

                await ctx.send(f"Now playing: {data['title']}")

            except Exception as e:
                await ctx.send(f"Error playing next song: {str(e)}")
        else:
            await ctx.send("Queue is empty. Add more songs!")

    @client.command(name="play")
    async def play(ctx, *, link):
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(e)

        try:
            if youtube_base_url not in link:
                query_string = urllib.parse.urlencode({
                    'search_query': link
                })

                content = urllib.request.urlopen(
                    youtube_results_url + query_string
                )

                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())

                link = youtube_watch_url + search_results[0]

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            song = data['url']
            volume = volume_levels.get(ctx.guild.id, 0.25)  # Default volume to 25% if not set
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': f'-vn -filter:a "volume={volume}"'
            }
            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
        except Exception as e:
            print(e)

    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("There is no queue to clear")

    @client.command(name="join")
    async def join(ctx):
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(e)

    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)

    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)

    @client.command(name="stop")
    async def stop(ctx):
        try:
            if ctx.guild.id in queues:
                queues[ctx.guild.id].clear()
                await ctx.send("Queue cleared!")
            if ctx.guild.id in voice_clients:
                await voice_clients[ctx.guild.id].disconnect()
                del voice_clients[ctx.guild.id]
                await ctx.send("Stopped playing and disconnected!")
            else:
                await ctx.send("There is no queue or active voice client to stop")
        except Exception as e:
            print(e)

    @client.command(name="skip")
    async def skip(ctx):
        guild_id = ctx.guild.id

        if guild_id in voice_clients and voice_clients[guild_id].is_playing():
            voice_clients[guild_id].stop()  # Stops the current song
            await play_next(ctx)  # Triggers next song
            await ctx.send("Skipped to the next song!")
        else:
            await ctx.send("No song is currently playing.")

    @client.command(name="skipto")
    async def skipto(ctx, index: int):
        guild_id = ctx.guild.id

        if guild_id in queues and 0 <= index < len(queues[guild_id]):
            queues[guild_id] = queues[guild_id][index:]  # Remove all previous songs in queue
            voice_clients[guild_id].stop()  # Stop current song
            await play_next(ctx)  # Start playing the chosen song
            await ctx.send(f"Skipped to song #{index + 1} in the queue!")
        else:
            await ctx.send("Invalid index or queue is empty.")

    @client.command(name="add")
    async def addtoqueue(ctx, *, link):
        guild_id = ctx.guild.id
        if guild_id not in queues:
            queues[guild_id] = []

        loop = asyncio.get_event_loop()
        
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
            
            if 'entries' in data:  # This means it's a playlist
                for entry in data['entries']:
                    if entry and 'url' in entry:
                        queues[guild_id].append({'title': entry['title'], 'url': entry['url']})  # Add title and URL to queue
                await ctx.send(f'Added {len(data["entries"])} tracks from the playlist to the queue!')
            else:  # Single track
                queues[guild_id].append({'title': data['title'], 'url': data['url']})
                await ctx.send(f'Added to queue: {data["title"]}')
        
        except Exception as e:
            await ctx.send("Error adding to queue: " + str(e))


    @client.command(name="queue")
    async def view_queue(ctx):
        guild_id = ctx.guild.id
        if guild_id in queues and queues[guild_id]:
            queue_list = [f"{i+1}. {song['title']}" for i, song in enumerate(queues[guild_id])]
            message = "Current queue:\n"

            # Send messages in chunks of 2000 characters
            for song in queue_list:
                if len(message) + len(song) + 2 > 2000:  # +2 accounts for newline characters
                    await ctx.send(message)
                    message = ""
                message += song + "\n"

            if message:  # Send remaining queue items
                await ctx.send(message)
        else:
            await ctx.send("The queue is empty.")

    @client.command(name="volume")
    async def setvolume(ctx, volume: int):
        guild_id = ctx.guild.id

        if guild_id in voice_clients:
            if 0 <= volume <= 100:
                volume_levels[guild_id] = volume / 100.0  # Store volume as a fraction (0.0 - 1.0)
                await ctx.send(f"Volume set to {volume}%")
            else:
                await ctx.send("Volume must be between 0 and 100")
        else:
            await ctx.send("No active voice client to set volume for")

    client.run(TOKEN)
