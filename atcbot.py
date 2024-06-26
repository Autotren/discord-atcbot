import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
import subprocess
import logging

# Set up logging configuration
logging.basicConfig(level=logging.INFO)

# Create a logger instance
logger = logging.getLogger(__name__)

intents = discord.Intents(guilds=True, voice_states=True, messages=True, message_content=True)

load_dotenv()
token = os.getenv('TOKEN')
prefix = os.getenv('PREFIX')
channel_id = int(os.getenv('CHANNEL_ID'))
role_name = os.getenv('ADMIN_ROLE')
udp_port = os.getenv('UDP_PORT')

disconnecting = False
player = None
client = commands.Bot(command_prefix=prefix,intents=intents)


@client.event
async def on_ready():
    logger.info('atcbot Ready')
    if (client.user.id in [member.id for member in client.get_channel(channel_id).members] and len(client.get_channel(channel_id).members) > 1) or (len(client.get_channel(channel_id).members) > 0 and not client.user.id in [member.id for member in client.get_channel(channel_id).members]):
        await play(None)

@client.event
async def on_voice_state_update(member, before, after):
    global disconnecting
    # logger.info('Voice state update: member = ' + str(member))
    # logger.info("before state = " + str(before))
    # logger.info("new state = " + str(after))
    # if member.id == client.user.id:
    #     # logger.info('Voice state update: member = ' + str(member) + " new state = " + str(after))
    #     logger.info("Disconnecting: " + str(disconnecting))
    #     logger.info("Channel: " + str(after.channel))
    #     logger.info("Saved link: " + link)

    if member.id == client.user.id and after.channel == None and disconnecting == False:
        logger.info("Unexpected disconnection detected, reconnecting...")
        await asyncio.sleep(5)
        try:
            logger.info("Trying to stop and cleanup any possible leftovers...")
            player.stop()
            player.cleanup()
        except:
            logger.info("Error when cleaning up!")
        
        logger.info("Reconnecting...")
        await play(None)
    elif  disconnecting == True:
        pass

    if before.channel is not None and before.channel.id == channel_id and player.is_connected() and len(client.get_channel(channel_id).members) <= 1:
        # logger.info("No listeners, waiting 15 minutes...")
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

    global player
    if player is not None and (player.is_connected() or player.is_playing()):
        logger.info("Player is already playing or connected, stopping...")
        player.stop()
    # elif client.user.id in [member.id for member in client.get_channel(channel_id).members]:
    #     logger.info("ALREADY PLAYING???")
    #     return
    else:
        logger.info("Connecting player to voice...")
        channel = client.get_channel(channel_id)
        player = await channel.connect(reconnect=False, self_deaf=True)

    global disconnecting
    disconnecting = False
    logger.info("Playing stream...")
    # player.play(discord.FFmpegPCMAudio(url, before_options="-fflags nobuffer -flags low_delay -probesize 32 -analyzeduration 0 -strict experimental", options="-flags low_delay")) # -loglevel debug -async 1

    nc_command = ['nc', '-ulp', udp_port]
    csdr_command = ['csdr', 'convert_f_s16']

    nc_process = subprocess.Popen(nc_command, stdout=subprocess.PIPE)
    csdr_process = subprocess.Popen(csdr_command, stdin=nc_process.stdout, stdout=subprocess.PIPE)

    # Create an FFmpegPCMAudio instance
    player.play(discord.FFmpegPCMAudio(csdr_process.stdout, pipe=True, before_options="-f s16le -ar 8000 -ac 1" , options="-loglevel debug"))

    # Wait for the player to finish playing the audio
    while player.is_playing():
        await asyncio.sleep(1)

    # Clean up the processes after audio playback is complete
    logger.info("Cleaning up subprocesses...")
    csdr_process.kill()
    nc_process.kill()

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
    logger.info("Is playing: " + str(player.is_playing()))


client.run(token)