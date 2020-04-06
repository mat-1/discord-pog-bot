import os
import re
import time
import utils
import asyncio
import discord
import motor.motor_asyncio
from betterbot import BetterBot


client = discord.Client()

betterbot = BetterBot(
	prefix='!',
	bot_id=696498215771701348
)


pog_channel_id = 696498388144750622
slow_pog_channel_id = 696576780764577812
slow_pog_timer = 10
slow_pog_amount = 20

dbclient = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('dburi'))

pog_db = dbclient.pogs


pog_count_coll = pog_db.pog_count

leaderboard_roles = (
	696520043139301407, #1
	696520111246409780, #2
	696520173540081714, #3
	696522358709813256, #4
	696522375092502638, #5
)

guild_id = 696496775292387369

async def add_pogs(user_id, amount):
	await pog_count_coll.update_one(
		{
			'id': user_id
		},
		{
			'$inc': {
				'pog_count': amount,
				'current_pog_count': amount,
			}
		},
		upsert=True
	)

async def add_pog(user_id):
	await add_pogs(user_id, 1)

async def set_pogs(user_id, amount):
	await pog_count_coll.update_one(
		{
			'id': user_id
		},
		{
			'$set': {
				'pog_count': amount,
				'current_pog_count': amount,
				'updated': True
			}
		},
		upsert=True
	)

async def get_pogs(user_id, current=True):
	doc = await pog_count_coll.find_one({
		'id': user_id
	})
	if not doc.get('updated'):
		await set_pogs(user_id, doc['pog_count'])
		doc = await pog_count_coll.find_one({
			'id': user_id
		})

	if current:
		return doc['current_pog_count']
	else:
		return doc['pog_count']
		


async def change_leaderboard_role(user, position):
	guild = client.get_guild(guild_id)
	print('user', user, type(user))
	member = guild.get_member(user)
	if not member: return
	print('member', member)
	if position != -1:
		role_id = leaderboard_roles[position]
		role = guild.get_role(role_id)
		await member.add_roles(role)
	else:
		role_id = None

	remove_roles = []
	for role in member.roles:
		if role.id in leaderboard_roles:
			if role.id != role_id:
				remove_roles.append(role)
	if remove_roles:
		print('Removing roles from', member)
		await member.remove_roles(*remove_roles)

async def update_leaderboard():
	leaderboard_tmp = await pog_db.leaderboard.find_one({
		'_id': 'leaderboard'
	})
	old_leaderboard = leaderboard_tmp['leaderboard']
	leaderboard = []
	async for user in pog_count_coll.find({}).sort('pog_count', -1).limit(5):
		leaderboard.append(user['id'])

	removed_users = []

	for position in range(5):
		new_user = leaderboard[position]
		try:
			old_user = old_leaderboard[position]
		except IndexError:
			old_user = None

		if old_user != new_user:
			await change_leaderboard_role(new_user, position)

		if old_user not in leaderboard:
			removed_users.append(old_user)
	for user in removed_users:
		if user:
			await change_leaderboard_role(user, -1)

	await pog_db.leaderboard.update_one({
		'_id': 'leaderboard'
	}, {
		'$set': {
			'leaderboard': leaderboard
		}
	})


@client.event
async def on_ready():
	print(f'We have logged in as {client.user}')
	channel_desc = client.get_channel(pog_channel_id).topic
	client.pog_count = int(channel_desc.replace('Pogs:', ''))
	asyncio.ensure_future(update_pog_desc())
	asyncio.ensure_future(update_pog_leaderboards())
	

def check_is_pog(message):
	pog_letter_before = '---'
	message = re.sub(r'<a?:([a-zA-Z0-9]*)(pog)([a-zA-Z0-9]*):([0-9]+)>', '', message, flags=re.IGNORECASE)
	for char in message:
		char = char.lower()
		if char == 'p' and pog_letter_before not in {'p','g','---'}:
			return False
		if char == 'o' and pog_letter_before not in 'po':
			return False
		if char == 'g' and pog_letter_before not in 'og':
			return False
		if char == 'e' and pog_letter_before not in 'g':
			return False
		if char == 'r' and pog_letter_before not in 'er':
			return False
		if char == 's' and pog_letter_before not in 'grs':
			return False
		if char in 'pogers':
			pog_letter_before = char
		if char not in '!?.pogers ':
			return False
	if pog_letter_before not in 'grs':
		return False
	return True

last_slow_pog_times = {}

@client.event
async def on_message(message):
	if message.channel.id not in {pog_channel_id, slow_pog_channel_id}:
		await betterbot.process_commands(message)
		return
	if not check_is_pog(message.content):
		return await message.delete()
	if message.channel.id == slow_pog_channel_id:
		client.pog_count += 20
		last_slow_pog_times[message.author.id] = time.time()
		await add_pogs(message.author.id, 20)
	else:
		client.pog_count += 1
		await add_pog(message.author.id)
	


@client.event
async def on_message_edit(before, message):
	if message.channel.id not in {pog_channel_id, slow_pog_channel_id}:
		return
	if not check_is_pog(message.content):
		return await message.delete()

async def update_pog_desc():
	pog_count_before = 0
	while True:
		await asyncio.sleep(2)
		if pog_count_before != client.pog_count:
			await client.get_channel(pog_channel_id).edit(topic=f'Pogs: {client.pog_count}')

		pog_count_before = client.pog_count

async def update_pog_leaderboards():
	while True:
		await update_leaderboard()
		await asyncio.sleep(60)


def start_bot():
	client.run(os.getenv('token'))

@betterbot.command('leaderboard', aliases=['leaderboards', 'lb', 'top'])
async def leaderboard(message, lb_max:int=5):
	m = []
	pos = 0
	async for user in pog_count_coll.find({}).sort('pog_count', -1).limit(lb_max):
		pos += 1
		id = user['id']
		count = user['pog_count']
		m.append(
			f'#{pos} - <@{id}> ({count})'
		)
	await message.channel.send(embed=discord.Embed(
		title='Leaderboard',
		description='\n'.join(m)
	))

@betterbot.command('setpogs')
async def setpogs(message, user:utils.Member, amount:int):
	print(amount)
	if message.author.id != 224588823898619905:
		return
	await set_pogs(user.id, amount)
	await message.channel.send(embed=discord.Embed(
		description=f'Set <@{user.id}>\'s pogs to {amount}'
	))

@betterbot.command('pogs', aliases=['pog'])
async def check_pogs(message, user:utils.Member=None):
	if user is None:
		user = message.author
	pog_count = await get_pogs(user.id)
	if user == message.author:
		msg = f'You have **{pog_count}** pogs'
	else:
		msg = f'<@{user.id}> has **{pog_count}** pogs'
	await message.channel.send(embed=discord.Embed(
		description=msg
	))

@betterbot.command('killpogs', aliases=['stealpogs'])
async def kill_pogs(message, user:utils.Member, amount:int):
	if not amount or amount <= 0:
		return await message.send('Invalid amount')
	elif user is None:
		return await message.send('Invalid user')
	killer_pog_count = await get_pogs(message.author.id)
	killee_pog_count = await get_pogs(user.id)

	if amount > killer_pog_count:
		return await message.send("You don't have enough pogs to do that")

	await add_pogs(message.author.id, -amount)
	await add_pogs(user.id, -amount)

	killer_new_pogs = killer_pog_count - amount
	killee_new_pogs = killee_pog_count - amount

	return await message.send(f'Aight, you now have {killer_new_pogs} pogs and your victim has {killee_new_pogs} pogs')

@betterbot.command('giftpogs', aliases=['givepogs'])
async def gift_pogs(message, user:utils.Member, amount:int):
	if not amount or amount <= 0:
		return await message.send('Invalid amount')
	elif user is None:
		return await message.send('Invalid user')
	gifter_pog_count = await get_pogs(message.author.id)
	giftee_pog_count = await get_pogs(user.id)

	if amount > gifter_pog_count:
		return await message.send("You don't have enough pogs to do that")

	await add_pogs(message.author.id, -amount)
	await add_pogs(user.id, amount)

	gifter_new_pogs = gifter_pog_count - amount
	giftee_new_pogs = giftee_pog_count + amount

	return await message.send(embed=discord.Embed(
		description=f'Aight, you now have {gifter_new_pogs} pogs and <@{user.id}> has {giftee_new_pogs} pogs'
	))

@betterbot.command('help')
async def help(message):
	return await message.send(
		'Commands:\n'
		'!pogs [user] - Tells you how many pogs you or the user have\n'
		'!killpogs <user> <amount> - Takes pogs from you and the user\n'
		'!giftpogs <user> <amount> - Takes pogs from you and gives them to the user\n'
		'!leaderboard [amount] - Tells you the users with the most pogs'
	)
