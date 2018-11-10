import asyncio
import aiohttp
import json
import discord
from discord import Game
from discord.ext import commands
from bottoken import TOKEN

BOT_PREFIX = "mark"
bot = commands.Bot(command_prefix=commands.when_mentioned_or(BOT_PREFIX))


if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '*{0.title}* uploaded by {0.uploader} and requested by {1.display_name}'
        duration = self.player.duration
        if duration:
            fmt = fmt + ' [length: {0[0]}m {0[1]}s]'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)

class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set() # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
            self.current.player.start()
            await self.play_next_song.wait()

class Music:
    """Voice related commands.
    Works in multiple servers at once.
    """
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(pass_context=True, no_pm=True)
    async def gehzu(self, ctx, *, channel : discord.Channel):
        """Joins a voice channel."""
        try:
            await self.create_voice_client(channel)
        except discord.ClientException:
            await self.bot.say('Already in a voice channel...')
        except discord.InvalidArgument:
            await self.bot.say('This is not a voice channel...')
        else:
            await self.bot.say('Ready to play audio in ' + channel.name)

    @commands.command(pass_context=True, no_pm=True)
    async def kommher(self, ctx):
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return True

    @commands.command(pass_context=True, no_pm=True)
    async def spielmal(self, ctx, *, song : str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.kommher)
            if not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            player.volume = 0.6
            entry = VoiceEntry(ctx.message, player)
            await self.bot.say('Enqueued ' + str(entry))
            await state.songs.put(entry)

    @commands.command(pass_context=True, no_pm=True)
    async def nichtsolaut(self, ctx, value : int):
        """Sets the volume of the currently playing song."""

        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say('Set the volume to {:.0%}'.format(player.volume))

    @commands.command(pass_context=True, no_pm=True)
    async def wartemal(self, ctx):
        """Pauses the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.pause()

    @commands.command(pass_context=True, no_pm=True)
    async def machweiter(self, ctx):
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.resume()

    @commands.command(pass_context=True, no_pm=True)
    async def gehweg(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    async def machnächste(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say('Requester requested skipping song...')
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            if total_votes >= 3:
                await self.bot.say('Skip vote passed, skipping song...')
                state.skip()
            else:
                await self.bot.say('Skip vote added, currently at [{}/3]'.format(total_votes))
        else:
            await self.bot.say('You have already voted to skip this song.')

    @commands.command(pass_context=True, no_pm=True)
    async def wasgeht(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if state.current is None:
            await self.bot.say('Not playing anything.')
        else:
            skip_count = len(state.skip_votes)
            await self.bot.say('Now playing {} [skips: {}/3]'.format(state.current, skip_count))


@bot.command(name='weristdercoolstehier',
                pass_context=True)
async def coolste(context):
    response = 'Du nicht'
    await bot.say(response + ", " + context.message.author.mention)
    voice = await bot.join_voice_channel(context.message.author.voice.voice_channel)
    player = voice.create_ffmpeg_player('resources/clips/cool.mp3')
    player.start()
    while not player.is_done():
        pass
    await voice.disconnect()


@bot.command(name='weristdercoolstehier2',
                pass_context=True)
async def coolste1(context):
    response = 'Du nicht'
    await bot.say(response + ", " + context.message.author.mention)
    voice = await bot.join_voice_channel(context.message.author.voice.voice_channel)
    player = voice.create_ffmpeg_player('resources/clips/cool2.mp3')
    player.start()


@bot.command(name='woistmeinknoppers',
                pass_context=True)
async def knoppers(context):
    voice = await bot.join_voice_channel(context.message.author.voice.voice_channel)
    player = voice.create_ffmpeg_player('resources/clips/knoppers.mp3')
    player.start()
    while not player.is_done():
        pass
    await voice.disconnect()

@bot.command(name='weristtim',
                pass_context=True)
async def timmeh(context):
    voice = await bot.join_voice_channel(context.message.author.voice.voice_channel)
    player = voice.create_ffmpeg_player('resources/clips/timmeh.mp3')
    player.start()
    while not player.is_done():
        pass
    await voice.disconnect()


@bot.command(name='wogehörtshawnhin',
                pass_context=True)
async def shawn(context):
    voice = await bot.join_voice_channel(context.message.author.voice.voice_channel)
    player = voice.create_ffmpeg_player('resources/clips/kammer.mp3')
    player.start()
    while not player.is_done():
        pass
    await voice.disconnect()


@bot.command(name='heyleute',
                pass_context=True)
async def heyleute(context):
    voice = await bot.join_voice_channel(context.message.author.voice.voice_channel)
    player = voice.create_ffmpeg_player('resources/clips/heyleute.mp3')
    player.start()
    while not player.is_done():
        pass
    await voice.disconnect()


@bot.command(name='kommeausderferne',
                pass_context=True)
async def kenning(context):
    voice = await bot.join_voice_channel(context.message.author.voice.voice_channel)
    player = voice.create_ffmpeg_player('resources/clips/kenning.mp3')
    player.start()
    while not player.is_done():
        pass
    await voice.disconnect()


@bot.command(name='haha',
                pass_context=True)
async def montelache(context):
    voice = await bot.join_voice_channel(context.message.author.voice.voice_channel)
    player = voice.create_ffmpeg_player('resources/clips/montelache.mp3')
    player.start()
    while not player.is_done():
        pass
    await voice.disconnect()


@bot.command(name='hahaha',
                pass_context=True)
async def nicomontelache(context):
    voice = await bot.join_voice_channel(context.message.author.voice.voice_channel)
    player = voice.create_ffmpeg_player('resources/clips/nicomontelache.mp3')
    player.start()
    while not player.is_done():
        pass
    await voice.disconnect()


@bot.command(pass_context=True)
async def leave(context):
    pass


@bot.event
async def on_ready():
    await bot.change_presence(game=Game(name="with Shawn's dick"))
    print('Logged in as:\n{0} (ID: {0.id})'.format(bot.user))

@bot.command()
async def bitcoin():
    url = 'https://api.coindesk.com/v1/bpi/currentprice/BTC.json'
    async with aiohttp.ClientSession() as session:  # Async HTTP request
        raw_response = await session.get(url)
        response = await raw_response.text()
        response = json.loads(response)
        await bot.say("Bitcoin price is: $" + response['bpi']['USD']['rate'])


async def list_servers():
    await bot.wait_until_ready()
    while not bot.is_closed:
        print("Current servers:")
        for server in bot.servers:
            print(server.name)
        await asyncio.sleep(600)

bot.add_cog(Music(bot))
bot.loop.create_task(list_servers())
bot.run(TOKEN)