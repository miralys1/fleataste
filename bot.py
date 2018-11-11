import asyncio
from discord import Game, Client
from bottoken import TOKEN

client = Client()


async def gelesen(msg):
    role = None
    for i in msg.server.roles:
        if str(i) == 'Community':
            role = i
    if role is None:
        print('Community Role wurde nicht gefunden')
        await client.send_message(msg.author, 'Anscheinend gibt es ein Problem beim Zuweisen der Rolle, '
                                              'bitte wende Dich an einen Admin :)')
    else:
        await client.add_roles(msg.author, role)


async def invite(msg):
    await client.send_message(msg.channel, 'https://discord.gg/duCsY9U')


@client.event
async def on_ready():
    await client.change_presence(game=Game(name="ist ZORNI"))
    print('Logged in as:\n{0} (ID: {0.id})'.format(client.user))


@client.event
async def on_message(msg):
    if msg.channel.name == 'willkommen':
        if msg.content == '?gelesen':
            await gelesen(msg)
        await client.delete_message(msg)
    elif msg.channel.name == 'bot':
        if msg.content == '?invite':
            await invite(msg)


async def list_servers():
    await client.wait_until_ready()
    while not client.is_closed:
        print("Current servers:")
        for server in client.servers:
            print(server.name)
        await asyncio.sleep(600)

client.loop.create_task(list_servers())
client.run(TOKEN)