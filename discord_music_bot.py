'''
discord_music_bot.py

Attempt to build a bot that plays music on discord

Plans:
    Change queue to dequeue ( :| )
    Implement Soundcloud support ( :) )
    Implement support for local files ( :| )
'''

from pytube import YouTube
from discord.ext import commands
from glob import glob
from sclib import SoundcloudAPI, Track
import discord
import sys
import os
import queue

# String constants
TOKEN = 'your_token_here'
OPATH = 'temp'
FILE = 'audio'
YT = 'youtube.com'
YT_ALT = 'youtu.be'
SC = 'soundcloud.com'

scapi = SoundcloudAPI()

playlist = queue.Queue(maxsize=10)  # change this to dequeue later

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
bot = commands.Bot(command_prefix='~', intents=intents)

# What's printed on the terminal if bot is running
@bot.event
async def on_ready():
    print(f'Logged on as {bot.user.name}')


# Joins without playing anything
@bot.command()
async def join(ctx):
    if ctx.author.voice is None:
        await ctx.send(f"Cannot join; {ctx.author.name} is not in VC")
        return
        
    voice_channel = ctx.author.voice.channel
    voice_client = await voice_channel.connect()
    await ctx.send(f"I'm in your area: {voice_channel.name}")
    

# Leaves voice channel and clears queue
@bot.command()
async def leave(ctx):
    if check_vc(ctx) == False: return
        
    bot.loop.create_task(clear_queue(ctx))
    await ctx.voice_client.disconnect()
    await ctx.send(f"Left {ctx.author.voice.channel.name}")
    

# Plays audio based on URL it's been sent
@bot.command()
async def play(ctx, url):
    if ctx.voice_client is None:
        await ctx.send("Attempting to join VC rn")
        await bot.loop.create_task(join(ctx))
        
    voice_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client
    
    if YT in url or YT_ALT in url:
        # User sends youtube link
        try:
            video = YouTube(url)
        except:
            await ctx.send("Bad YT URL")
            return
        audio = video.streams.filter(only_audio=True).first()
        print(video.title)
        audio_file = audio.download(output_path=OPATH, filename=video.title)
    elif SC in url:
        # User sends soundcloud link; code taken from soundcloud-lib documentation
        try:
            audio = scapi.resolve(url)
        except:
            await ctx.send("Bad SC URL")
            return
        temp = f'{audio.artist} - {audio.title}'
        audio_file = OPATH + '/' + temp
        with open(audio_file, 'wb+') as file:
            audio.write_mp3_to(file)
    else:
        # Link is invalid
        await ctx.send("Invalid URL; Try again")
        return


    try:
        playlist.put(audio_file)
    except:
        # Exception is here for if the queue is full
        # We remove the audio file in this case
        ctx.send("Could not add to queue")
        os.remove(audio_file)
        return

    # Add track to queue or play it right away
    if voice_client.is_playing() or voice_client.is_paused():
        await ctx.send(f"Added {os.path.basename(audio_file)} to queue")
    else:
        await play_next(ctx)
    

# Pauses whatever audio is currently playing
@bot.command()
async def pause(ctx):

    if check_vc(ctx) == False: return

    voice_client = ctx.voice_client
    if voice_client.is_playing():
        await ctx.send("Pausing...")
        voice_client.pause()
    else:
        await ctx.send("Already paused sir")
    

# Resumes audio if audio is playing
@bot.command()
async def resume(ctx):

    if check_vc(ctx) == False: return
        
    voice_client = ctx.voice_client
    if voice_client.is_paused():
        await ctx.send("Playing...")
        voice_client.resume()
    else:
        await ctx.send("Already playing sir")
    

# Stops music that is currently playing on the queue
@bot.command()
async def skip(ctx):
    if check_vc(ctx) == False: return
        
    voice_client = ctx.voice_client
    voice_client.stop()
    
    if playlist.empty() == False:
        bot.loop.create_task(play_next(ctx))


# Prints queue
@bot.command()
async def queue(ctx):
    if playlist.empty():
        await ctx.send("Queue is empty")
        return
        
    queue_list = list(playlist.queue)
    print(queue_list)
    for item in queue_list:
        await ctx.send(os.path.basename(item))


# Clears queue and deletes local files
@bot.command()
async def clear_queue(ctx):
    while playlist.empty() == False:
        audio_file = playlist.get()
        os.remove(audio_file)
    await ctx.send("Queue is now empty")
    

# Removes top item from queue
@bot.command()
async def remove_next(ctx):
    if playlist.empty():
        await ctx.send("Queue is empty")
        return
        
    audio_file = playlist.get()
    await ctx.send(f"Removing {os.path.basename(audio_file)}")
    os.remove(audio_file)


# Use dequeue instead
@bot.command()
async def remove_last(ctx):
    if playlist.empty():
        await ctx.send("Queue is empty")
        return
        
    await ctx.send("Developer hasn't implemented this yet")


# Administrator commands
# Remove previous message history from bot
@bot.command()
@commands.has_permissions(administrator=True)
async def clear_history(ctx, limit):
    channel = ctx.channel
    limit = int(limit)
    async for message in channel.history(limit=limit+1):
        await message.delete()
        
    await ctx.send(f"Deleted past {limit} messages")


# Wipes entire chat history in a channel
@bot.command()
@commands.has_permissions(administrator=True)
async def wipe(ctx):
    channel = ctx.channel
    async for message in channel.history(limit=None):
        await message.delete()
        
    await ctx.send("Wiped history")


# This command is for putting the bot offline manually from the discord app itself
# Can only be called by the administrator for testing purposes
@bot.command()
@commands.has_permissions(administrator=True)
async def disconnect(ctx):
    await ctx.send("Got it boss")
    await bot.close()


# Command that doesn't currently work
@bot.command()
@commands.has_permissions(administrator=True)
async def Ham(ctx):
    await ctx.send("Got it boss")
    audio_file = "audio.opus"
    
    voice_client = ctx.voice_client
    
    bot.loop.create_task(clear_queue(ctx))
    bot.loop.create_task(skip(ctx))
    voice_client.stop()
    print("Foo")
    voice_client.play(discord.FFmpegPCMAudio(audio_file))
    print("Bar")


# Non commands that are called by the bot
# Plays next track in queue
async def play_next(ctx):
    audio_file = playlist.get()
    voice_client = ctx.voice_client
    await ctx.send(f"Now Playing: {os.path.basename(audio_file)}")
    
    def after_playing(error):
        os.remove(audio_file)
        if playlist.empty() == False:
            bot.loop.create_task(play_next(ctx))
    
    voice_client.play(discord.FFmpegPCMAudio(audio_file), after=after_playing)


# Checks if bot or user is in a voice channel
def check_vc(ctx):
    if ctx.voice_client is None or ctx.author.voice is None:
        print("Can't do this action")
        return False
    else:
        print("In VC")
        return True


bot.run(TOKEN)


