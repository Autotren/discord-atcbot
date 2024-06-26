import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv

intents = discord.Intents(guilds=True, voice_states=True, messages=True, message_content=True)

load_dotenv()
token = os.getenv('TOKEN')
prefix = os.getenv('PREFIX')
channel_id = int(os.getenv('CHANNEL_ID'))
default_link = os.getenv('DEFAULT_LINK')
role_name = os.getenv('ADMIN_ROLE')

disconnecting = False
player = None
client = commands.Bot(command_prefix=prefix,intents=intents)


@client.event
async def on_ready():
    print('DiscStream Ready')
    if (client.user.id in [member.id for member in client.get_channel(channel_id).members] and len(client.get_channel(channel_id).members) > 1) or (len(client.get_channel(channel_id).members) > 0 and not client.user.id in [member.id for member in client.get_channel(channel_id).members]):
        await play(None)
    # await play(None)

# @client.event
# async def on_error(event, *args, **kwargs):
#     # Handle the error that occurred
#     print("An error occurred: ", event)

@client.event
async def on_voice_state_update(member, before, after):
    global disconnecting
    global link
    # print('Voice state update: member = ' + str(member))
    # print("before state = " + str(before))
    # print("new state = " + str(after))
    # if member.id == client.user.id:
    #     # print('Voice state update: member = ' + str(member) + " new state = " + str(after))
    #     print("Disconnecting: " + str(disconnecting))
    #     print("Channel: " + str(after.channel))
    #     print("Saved link: " + link)

    if member.id == client.user.id and after.channel == None and disconnecting == False:
        print("Unexpected disconnection detected, reconnecting...")
        await asyncio.sleep(5)

        try:
            print("Trying to stop and cleanup any possible leftovers...")
            player.stop()
            player.cleanup()
        except:
            print("Error when cleaning up!")
        
        print("Reconnecting with saved link: " + link)
        await play(None, link)
    elif  disconnecting == True:
        pass

    if before.channel is not None and before.channel.id == channel_id and player.is_connected() and len(client.get_channel(channel_id).members) <= 1:
        # print("No listeners, waiting 15 minutes...")
        # await asyncio.sleep(10)
        # if len(client.get_channel(channel_id).members) > 1:
        #     return
        # Stop the audio and clean up the player
        player.stop()
        player.cleanup()

        # Disconnect from the voice channel
        disconnecting = True
        await player.disconnect()

    if member.id != client.user.id and after.channel is not None and after.channel.id == channel_id and len(client.get_channel(channel_id).members) > 0 and (player is None or not player.is_connected()):
        # Invoke play() if the bot is not already connected
        await play(None)


@client.command(aliases=['p', 'pla'])
async def play(ctx, url: str=None):
    # channel = ctx.message.author.voice.channel
    # Check for role
    if ctx is not None:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None or role not in ctx.author.roles:
            return

    global link
    global default_link
    if url == None:
        url = default_link
    else:
        link = url
    global player
    if player is not None and (player.is_connected() or player.is_playing()):
        print("Player is already playing or connected, stopping...")
        player.stop()
    # elif client.user.id in [member.id for member in client.get_channel(channel_id).members]:
    #     print("ALREADY PLAYING???")
    #     return
    else:
        print("Connecting player to voice...")
        channel = client.get_channel(channel_id)
        player = await channel.connect(reconnect=False, self_deaf=True)

    global disconnecting
    disconnecting = False
    print("Playing file: " + url)
    player.play(discord.FFmpegPCMAudio(url, before_options="-fflags nobuffer -flags low_delay -probesize 32 -analyzeduration 0 -strict experimental", options="-flags low_delay")) # -loglevel debug -async 1


@client.command(aliases=['s', 'sto'])
async def stop(ctx):
    # Check for role
    if ctx is not None:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None or role not in ctx.author.roles:
            return

    global disconnecting
    disconnecting = True
    player.stop()
    await player.disconnect()
    player.cleanup()

@client.command()
async def stat(ctx):
    print("Is playing: " + str(player.is_playing()))


client.run(token)