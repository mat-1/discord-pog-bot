from discord.ext import commands
import discordbot
import discord
import re

def get_channel_members(channel_id):
	return discordbot.client.get_channel(channel_id).members

def check_user_id(ctx, arg):
	try:
		member = ctx.guild.get_member(int(arg))
		if member is not None:
			return member
	except ValueError:
		pass


def check_mention(ctx, arg):
	match = re.fullmatch(r'<@!?(\d+)>', arg)
	if match:
		user_id = match.group(1)
		try:
			member = ctx.guild.get_member(int(user_id))
			if member is not None:
				return member
		except ValueError:
			# doesnt happen i think
			# but i dont want to break it
			pass


def check_name_with_discrim(ctx, arg):
	member = discord.utils.find(
		lambda m: str(m).lower() == arg.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_name_without_discrim(ctx, arg):
	member = discord.utils.find(
		lambda m: m.name.lower == arg.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_nickname(ctx, arg):
	member = discord.utils.find(
		lambda m: m.display_name.lower() == arg.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_name_starts_with(ctx, arg):
	member = discord.utils.find(
		lambda m: m.name.lower().startswith(arg.lower()),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_nickname_starts_with(ctx, arg):
	member = discord.utils.find(
		lambda m: m.display_name.lower().startswith(arg.lower()),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_name_contains(ctx, arg):
	member = discord.utils.find(
		lambda m: arg.lower() in m.name.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_nickname_contains(ctx, arg):
	member = discord.utils.find(
		lambda m: arg.lower() in m.display_name.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member

class Member(commands.Converter):
	async def convert(self, ctx, arg):
		if arg[0] == '@':
			arg = arg[1:]
		
		# these comments suck but i dont really want to remove them
		# also this should be a module-level constant
		# but this module is too big already
		CHECKERS = [
			check_user_id, # Check user id
			check_mention, # Check mention
			check_name_with_discrim, # Name + discrim
			# check_name_with_discrim was repeated for some reason
			# i hope removing it doesnt break something
			check_nickname, # Nickname
			check_name_starts_with, # Name starts with
			check_nickname_starts_with, # Nickname starts with
			check_name_contains, # Name contains
			check_nickname_contains, # Nickname contains
		]
		for checker in CHECKERS:
			member = checker(ctx, arg)
			if member is not None:
				return member
		
		return None