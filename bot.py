import asyncio
from discord import Client
import discord
from bottoken import TOKEN

client = Client()


async def gelesen(msg):
    role = None
    for i in msg.guild.roles:
        if str(i) == 'Community':
            role = i
    if role is None:
        print('Community Role wurde nicht gefunden')
        await msg.author.send('Anscheinend gibt es ein Problem beim Zuweisen der Rolle, '
                              'bitte wende Dich an einen Admin :)')
    else:
        await msg.author.add_roles(role)


async def invite(msg):
    await msg.channel.send('https://discord.gg/uDThPZw')


@client.event
async def on_ready():
    activity = discord.Game("ist ZORNI")
    await client.change_presence(activity=activity)
    print('Logged in as:\n{0} (ID: {0.id})'.format(client.user))


@client.event
async def on_message(msg):
    if isinstance(msg.channel, discord.abc.GuildChannel):
        if msg.channel.name == 'willkommen':
            if msg.content == '?gelesen':
                await gelesen(msg)
            await msg.delete()
        elif msg.channel.name == 'bot':
            if msg.content == '?invite':
                await invite(msg)


async def list_guilds():
    await client.wait_until_ready()
    while not client.is_closed():
        print("Current guilds:")
        for guild in client.guilds:
            print(guild.name)
        await asyncio.sleep(600)

client.loop.create_task(list_guilds())
client.run(TOKEN)
