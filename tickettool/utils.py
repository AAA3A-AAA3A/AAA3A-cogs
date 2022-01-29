import discord
import asyncio
from redbot.core import commands
from dislash import ActionRow, Button, ButtonStyle
import typing
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.menus import start_adding_reactions

class utils():
    def __init__(self, bot):
        self.bot = bot

    async def get_overwrites(self, ticket):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        overwrites = {
            ticket.owner: discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                attach_files=True,
            ),
            ticket.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                attach_files=True,
                manage_messages=True,
                manage_channels=True,
                manage_permissions=True,
            ),
            ticket.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
            )
        }
        if ticket.claim is not None:
            overwrites[ticket.claim] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                )
            )
        if config["admin_role"] is not None:
            overwrites[config["admin_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                    manage_messages=True,
                )
            )
        if config["support_role"] is not None:
            overwrites[config["support_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                )
            )
        if config["view_role"] is not None:
            overwrites[config["view_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    add_reactions=False,
                )
            )
        return overwrites

    _ReactableEmoji = typing.Union[str, discord.Emoji]

    async def ConfirmationAsk(
            self,
            ctx,
            text: typing.Optional[str]=None,
            embed: typing.Optional[discord.Embed]=None,
            file: typing.Optional[discord.File]=None,
            timeout: typing.Optional[int]=60,
            timeout_message: typing.Optional[str]="Timed out, please try again",
            use_reactions: typing.Optional[bool]=True,
            message: typing.Optional[discord.Message]=None,
            put_reactions: typing.Optional[bool]=True,
            delete_message: typing.Optional[bool]=True,
            reactions: typing.Optional[typing.Iterable[_ReactableEmoji]]=["✅", "❌"],
            check_owner: typing.Optional[bool]=True,
            members_authored: typing.Optional[typing.Iterable[discord.Member]]=[]):
        if message is None:
            if not text and not embed and not file:
                if use_reactions:
                    text = "To confirm the current action, please use the feedback below this message."
                else:
                    text = "To confirm the current action, please send yes/no in this channel."
            message = await ctx.send(content=text, embed=embed, file=file)
        if use_reactions:
            if put_reactions:
                try:
                    start_adding_reactions(message, reactions)
                except discord.HTTPException:
                    use_reactions = False
        async def delete_message(message: discord.Message):
            try:
                return await message.delete()
            except discord.HTTPException:
                pass
        if use_reactions:
            end_reaction = False
            def check(reaction, user):
                if check_owner:
                    return user == ctx.author or user.id in ctx.bot.owner_ids or user in members_authored and str(reaction.emoji) in reactions
                else:
                    return user == ctx.author or user in members_authored and str(reaction.emoji) in reactions
                # This makes sure nobody except the command sender can interact with the "menu"
            while True:
                try:
                    reaction, abc_author = await ctx.bot.wait_for("reaction_add", timeout=timeout, check=check)
                    # waiting for a reaction to be added - times out after x seconds
                    if str(reaction.emoji) == reactions[0]:
                        end_reaction = True
                        if delete_message:
                            await delete_message(message)
                        return True
                    elif str(reaction.emoji) == reactions[1]:
                        end_reaction = True
                        if delete_message:
                            await delete_message(message)
                        return False
                    else:
                        try:
                            await message.remove_reaction(reaction, abc_author)
                        except discord.HTTPException:
                            pass
                except asyncio.TimeoutError:
                    if not end_reaction:
                        if delete_message:
                            await delete_message(message)
                        if timeout_message is not None:
                            await ctx.send(timeout_message)
                        return None
        if not use_reactions:
            def check(msg):
                if check_owner:
                    return msg.author == ctx.author or msg.author.id in ctx.bot.owner_ids or msg.author in members_authored and msg.channel is ctx.channel
                else:
                    return msg.author == ctx.author or msg.author in members_authored and msg.channel is ctx.channel
                # This makes sure nobody except the command sender can interact with the "menu"
            try:
                end_reaction = False
                check = MessagePredicate.yes_or_no(ctx)
                msg = await ctx.bot.wait_for("message", timeout=timeout, check=check)
                # waiting for a a message to be sended - times out after x seconds
                if check.result:
                    end_reaction = True
                    if delete_message:
                        await delete_message(message)
                    await delete_message(msg)
                    return True
                else:
                    end_reaction = True
                    if delete_message:
                        await delete_message(message)
                    await delete_message(msg)
                    return False
            except asyncio.TimeoutError:
                if not end_reaction:
                    if delete_message:
                        await delete_message(message)
                    if timeout_message is not None:
                        await ctx.send(timeout_message)
                    return None