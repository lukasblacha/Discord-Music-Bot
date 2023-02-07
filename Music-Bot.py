import asyncio
from datetime import timedelta
import yt_dlp
import discord
import logging
import argparse
from discord.ext import commands
from discord import Embed

banner = """
   \  |              _)             __ )          |   
  |\/ |  |   |   __|  |   __|       __ \    _ \   __| 
  |   |  |   | \__ \  |  (  _____|  |   |  (   |  |   
 _|  _| \__,_| ____/ _| \___|      ____/  \___/  \__| 
"""
version = "0.1"
success = "**Success ✅**\n"
warning = "**Warning ℹ️**\n"
error = "**Error ❗️**\n"
logging.basicConfig(level=logging.INFO)
parser = argparse.ArgumentParser()
parser.add_argument("-t", "--token", help="Bot TOKEN")
args = parser.parse_args()

if args.token == None:
    print(f"{banner}\n\nPLEASE PROVIDE BOT A TOKEN BY RUNNING LIKE THE FOLLOWING:")
    print("\n")
    print(">>> python3 Music-Bot.py -t TOKEN <<<")
else:

    # Suppress noise about console usage from errors
    yt_dlp.utils.bug_reports_message = lambda: ""

    ytdl_format_options = {
        "format": "bestaudio/mp3",
        "outtmpl": "cache/%(extractor)s-%(id)s-%(title)s.mp3",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0",  # Bind to ipv4 since ipv6 addresses cause issues at certain times
        "postprocessors": [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '1080',
        }],
    }

    ffmpeg_options = {"options": "-vn"}

    ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


    class YTDLSource(discord.PCMVolumeTransformer):
        def __init__(self, source: discord.AudioSource, *, data: dict, volume: float = 0.5):
            super().__init__(source, volume)

            self.data = data

            self.title = data.get("title")
            self.url = data.get("url")

        @classmethod
        async def from_url(cls, url, *, loop=None, stream=False):
            loop = loop or asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(url, download=not stream)
            )

            if "entries" in data:
                # Takes the first item from a playlist
                data = data["entries"][0]

            filename = data["url"] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(
        command_prefix=commands.when_mentioned_or("!"),
        description="Relatively simple music bot example",
        intents=intents,
    )


    @bot.event
    async def on_ready():
        print(banner)
        print(f"Bot Version: {version}")
        print(f"Bot: {bot.user} (ID: {bot.user.id})")
        print(
            f"Invitation LINK: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=968552344896&scope=bot%20applications.commands")
        print("------")


    @bot.slash_command(name="join", description="Summon the bot into your channel")
    async def join(ctx: commands.Context):
        try:
            channel = ctx.author.voice.channel
        except Exception as err:
            print(err)
        if channel is None:
            await ctx.send(f"{error}You are not in a voice-channel! Could not join...")
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await ctx.respond(f"{success}Connected to `{channel.name}`")
        await channel.connect()


    @bot.slash_command(name="nowplaying", descriprion="Show details what the bot is currently playing")
    async def nowplaying(ctx: commands.Context):
        async with ctx.channel.typing():
            if ctx.voice_client is None:
                embed = Embed(title=f"{error}Currently is no music playing!", color=discord.Color.red())
            else:
                embed = Embed(title=f"⏯  Now playing", color=discord.Color.blue())
                embed.add_field(name="🎵 ️ Title", value=ctx.voice_client.source.title, inline=False)
                embed.add_field(name="🔗 Link",
                                value=f"https://youtube.com/watch?v={ctx.voice_client.source.data['id']}", inline=False)
                embed.add_field(name="🔈 Volume",
                                value=f"Current setting `{int(ctx.voice_client.source.volume * 100)}%`", inline=False)
                embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
                embed.set_image(url=f"https://i3.ytimg.com/vi/{ctx.voice_client.source.data['id']}/maxresdefault.jpg")
                embed.set_footer(text=f"{round(bot.latency, 2)}ms Latency 🚀")
            await ctx.respond(embed=embed)


    @bot.slash_command(name="play", description="Plays a song from YouTube [With preloading]")
    async def play(ctx: commands.Context, url: str):
        async with ctx.typing():
            await ctx.respond("🤖 Your song is queued for download... please wait ", ephemeral=True)
            try:
                player = await YTDLSource.from_url(url, loop=bot.loop)
                ctx.voice_client.play(
                    player, after=lambda e: print(f"Player error: {e}") if e else None
                )
            except discord.HTTPException as err:
                raise commands.CommandError(err)
            finally:
                await ctx.send(f"{success}Now playing: `{player.title}`\nRequested by {ctx.author.mention}")


    @bot.slash_command(name="stream", description="Streams a song from YouTube [Without preloading]")
    async def stream(ctx: commands.Context, url: str):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            ctx.voice_client.play(
                player, after=lambda e: print(f"Player error: {e}") if e else None
            )

        await ctx.respond(f"{success}Now playing: `{player.title}`\nRequested by {ctx.author.mention}")


    @bot.slash_command(name="pause", description="Pauses the playback")
    async def _pause(ctx: commands.Context):
        ctx.voice_client.pause()
        await ctx.respond(f"{success}⏸️ {ctx.author} has paused the playback")


    @bot.slash_command(name="resume", description="Resumes the playback")
    async def _resume(ctx: commands.Context):
        ctx.voice_client.resume()
        await ctx.respond(f"{success}▶️ {ctx.author} has resumed the playback")


    @bot.slash_command(name="volume", description="Sets the bot volume")
    async def volume(ctx: commands.Context, volume: int):
        if ctx.voice_client is None:
            return await ctx.send(f"{error}Not connected to a voice channel.")
        ctx.voice_client.source.volume = volume / 100
        await ctx.respond(f"{success}Changed volume to `{volume}%`")


    @bot.slash_command(name="stop", description="Stopps the playback and disconnects the Bot")
    async def stop(ctx: commands.Context):
        await ctx.respond(f"{success}Stopping playback in `{ctx.voice_client.channel.name}`")
        await ctx.voice_client.disconnect(force=True)


    @play.before_invoke
    @stream.before_invoke
    async def ensure_voice(ctx: commands.Context):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


    @bot.event
    async def on_application_command_error(ctx, error):
        print(f"[on_application_command_error]\n{ctx.author}\n{error}")
        if isinstance(error, discord.ext.commands.CommandError):
            cool_down_time = int(error.cooldown.get_retry_after())
            td = timedelta(seconds=cool_down_time)
            embed = Embed(title=f"{warning}Dieser Command befindet sich im Cool Down!\n Versuche es in `{td}` nochmal!",
                          color=15158332)
        elif isinstance(error, discord.ext.commands.CommandOnCooldown):
            cool_down_time = int(error.cooldown.get_retry_after())
            td = timedelta(seconds=cool_down_time)
            embed = Embed(title=f"{warning}Dieser Command befindet sich im Cool Down!\n Versuche es in `{td}` nochmal!",
                          color=15158332)
        else:
            embed = Embed(title=f"{error}", color=15158332)
        await ctx.respond(embed=embed)


    @bot.event
    async def on_command_error(ctx, error):
        print(f"[on_command_error]\n{ctx.author}\n{error}")
        embed = Embed(title=f"{error}", color=15158332)
        await ctx.send(embed=embed)


    bot.run(args.token)
