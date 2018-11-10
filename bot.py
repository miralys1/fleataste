import asyncio
from discord import Game
from discord.ext import commands
from bottoken import TOKEN

BOT_PREFIX = "!"
bot = commands.Bot(command_prefix=commands.when_mentioned_or(BOT_PREFIX))

@bot.command(name='gelesen',
                pass_context=True)
async def on_message(context):
    role = None
    for i in context.message.server.roles:
        if str(i) == 'Community':
            role = i
    await bot.add_roles(context.message.author, role)
    await bot.delete_message(context.message)

@bot.event
async def on_ready():
    await bot.change_presence(game=Game(name="ist ZORNI"))
    print('Logged in as:\n{0} (ID: {0.id})'.format(bot.user))


async def list_servers():
    await bot.wait_until_ready()
    while not bot.is_closed:
        print("Current servers:")
        for server in bot.servers:
            print(server.name)
        await asyncio.sleep(600)

bot.loop.create_task(list_servers())
bot.run(TOKEN)