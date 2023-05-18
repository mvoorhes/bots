'''
discord_music_bot.py

Attempt to build a bot that plays music on discord
'''

TOKEN = 'your_token_here'
OPATH = 'temp'
FILE = 'audio'

import discord
import sys
from pytube import YouTube
from discord.ext import commands
import os
from glob import glob
import queue


playlist = queue.Queue(maxsize=10)

# Was going to use below code (up until return filename) until I realized I can just use video.title as the filename
character = '0'
filename = 'audio' + character

def update_filename(filename, character):
    integer = ord(character)
    integer += 1
    filename = filename.replace(character, chr(integer))
    character = chr(integer)
    return filename, character


intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
bot = commands.Bot(command_prefix='~', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged on as {bot.user.name}')


@bot.command()
async def join(ctx):
    if ctx.author.voice is None:
        await ctx.send('Cannot join')
        return
        
    voice_channel = ctx.author.voice.channel
    voice_client = await voice_channel.connect()
    await ctx.send(f"I'm in your area: {voice_channel.name}")
    

@bot.command()
async def leave(ctx):
    if ctx.voice_client is None:
        await ctx.send("Not in VC rn, I must go offline")
        return
        
    bot.loop.create_task(clear_queue(ctx))
    
        
    await ctx.voice_client.disconnect()
    await ctx.send(f"Left {ctx.author.voice.channel.name}")
    
    
@bot.command()
async def play(ctx, url):
    if ctx.voice_client is None:
        await ctx.send("Attempting to join VC rn")
        try:
            await bot.loop.create_task(join(ctx))
        except:
            await ctx.send("Try ~join first before attempting to play anything")
        
    voice_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client
        
    video = YouTube(url)
    audio = video.streams.filter(only_audio=True).first()
    print(video.title)

    audio_file = audio.download(output_path=OPATH, filename=video.title)

    try:
        playlist.put(audio_file)
    except:
        ctx.send("Could not add to queue")
        return

    # Add track to queue or play it right away
    if voice_client.is_playing() or voice_client.is_paused():
        await ctx.send("Added to queue")
    else:
        await play_next(ctx)
    

# Pauses whatever audio is currently playing
@bot.command()
async def pause(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not even in a voice channel.")
        return

    voice_client = ctx.voice_client
    if voice_client.is_playing():
        await ctx.send("Pausing...")
        voice_client.pause()
    else:
        await ctx.send("Already paused sir")
    

# Resumes audio if audio is playing
@bot.command()
async def resume(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not even in a voice channel.")
        return
        
    voice_client = ctx.voice_client
    if voice_client.is_paused():
        await ctx.send("Playing...")
        voice_client.resume()
    else:
        await ctx.send("Already playing sir")
    

# Stops music that is currently playing on the queue
@bot.command()
async def skip(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not even in a voice channel.")
        return
        
    voice_client = ctx.voice_client
    voice_client.stop()
    
    if playlist.empty() == False:
        bot.loop.create_task(play_next(ctx))



@bot.command()
async def queue(ctx):
    if playlist.empty():
        await ctx.send("Queue is empty")
        return
        
    queue_list = list(playlist.queue)
    print(queue_list)
    for item in queue_list:
        await ctx.send(os.path.basename(item))


@bot.command()
async def clear_queue(ctx):
    while playlist.empty() == False:
        audio_file = playlist.get()
        os.remove(audio_file)
    await ctx.send("Queue is now empty")


# This command is for putting the bot offline manually from the discord app itself
@bot.command()
@commands.has_permissions(administrator=True)
async def disconnect(ctx):
    await ctx.channel.send("Got it boss")
    sys.exit(1)



# Non bot commands
async def play_next(ctx):
    audio_file = playlist.get()
    voice_client = ctx.voice_client
    
    def after_playing(error):
        os.remove(audio_file)
        if playlist.empty() == False:
            bot.loop.create_task(play_next(ctx))
    
    voice_client.play(discord.FFmpegPCMAudio(audio_file), after=after_playing)


# Checks if bot is in a voice channel
async def check_vc(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not even in a voice channel")
        return False
    return True

bot.run(TOKEN)


