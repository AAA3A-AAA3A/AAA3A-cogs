from .AAA3A_utils.cogsutils import CogsUtils
import discord
import typing
from redbot.core import commands, Config
from dislash import ActionRow
from .converters import RoleEmojiConverter

# Credits:
# Thanks to TrustyJAID for the two converter for the bulk command arguments! (https://github.com/TrustyJAID/Trusty-cogs/blob/main/roletools/converter.py)
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

def _(untranslated: str):
    return untranslated

class RolesButtons(commands.Cog):
    """A cog to have roles-buttons!"""

    def __init__(self, bot):
        self.bot = bot
        self.config: Config = Config.get_conf(
            self,
            identifier=370638632963,
            force_registration=True,
        )
        self.roles_button_guild = {
            "roles_buttons": {},
        }

        self.config.register_guild(**self.roles_button_guild)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        guild = inter.guild
        channel = inter.channel
        if inter.author is None:
            return
        if inter.guild is None:
            return
        if inter.author.bot:
            return
        if await self.bot.cog_disabled_in_guild(self, guild):
            return
        if not inter.component.custom_id.startswith("roles_buttons"):
            return
        config = await self.config.guild(guild).roles_buttons.all()
        if not f"{inter.channel.id}-{inter.message.id}" in config:
            return
        if getattr(inter.component.emoji, "id", None):
            inter.component.emoji = str(inter.component.emoji.id)
        else:
            inter.component.emoji = str(inter.component.emoji).strip("\N{VARIATION SELECTOR-16}")
        if not f"{inter.component.emoji}" in config[f"{inter.channel.id}-{inter.message.id}"]:
            return
        role = inter.guild.get_role(config[f"{inter.channel.id}-{inter.message.id}"][f"{inter.component.emoji}"]["role"])
        if role is None:
            inter.respond(_("The role I have to put you in no longer exists. Please notify an administrator of this server.").format(**locals()), ephemeral=True)
            return
        if not role in inter.author.roles:
            try:
                await inter.author.add_roles(role, reason=_("Role-button of {inter.message.id} in {channel.id}.").format(**locals()))
            except discord.HTTPException:
                await inter.respond(_("I could not add the {role.mention} ({role.id}) role to you. Please notify an administrator of this server.").format(**locals()), ephemeral=True)
                return
            else:
                await inter.respond(_("You now have the role {role.mention} ({role.id}).").format(**locals()), ephemeral=True)
        else:
            try:
                await inter.author.remove_roles(role, reason=f"Role-button of {inter.message.id} in {channel.id}.")
            except discord.HTTPException:
                await inter.respond(_("I could not remove the {role.mention} ({role.id}) role to you. Please notify an administrator of this server.").format(**locals()), ephemeral=True)
                return
            else:
                await inter.respond(_("I did remove the role {role.mention} ({role.id}).").format(**locals()), ephemeral=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild:
            return
        config = await self.config.guild(message.guild).roles_buttons.all()
        if not f"{message.channel.id}-{message.id}" in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).roles_buttons.set(config)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.group()
    async def rolesbuttons(self, ctx: commands.Context):
        """Group of commands for use ReactToCommand.
        """
        pass

    @rolesbuttons.command()
    async def add(self, ctx: commands.Context, message: discord.Message, role: discord.Role, button: typing.Union[discord.Emoji, str], *, text_button: typing.Optional[str]=None):
        """Add a role-button to a message.
        """
        if not message.author == ctx.guild.me:
            await ctx.send(_("I have to be the author of the message for the role-button to work.").format(**locals()))
            return
        permissions = message.channel.permissions_for(ctx.guild.me)
        if not permissions.add_reactions or not permissions.read_message_history or not permissions.read_messages or not permissions.view_channel:
            await ctx.send(_("I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to see the messages in that channel.").format(**locals()))
            return
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if not f"{message.channel.id}-{message.id}" in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) == 25:
            await ctx.send(_("I can't do more than 25 roles-buttons for one message.").format(**locals()))
            return
        if hasattr(button, 'id'):
            config[f"{message.channel.id}-{message.id}"][f"{button.id}"] = {"role": role.id, "text_button": text_button}
        else:
            config[f"{message.channel.id}-{message.id}"][f"{button}"] = {"role": role.id, "text_button": text_button}
        try:
            await message.edit(components=self.get_buttons(config, message))
        except discord.HTTPException:
            await ctx.send(_("I can't do more than 25 roles-buttons for one message.").format(**locals()))
            return
        await self.config.guild(ctx.guild).roles_buttons.set(config)
        await ctx.tick()

    @rolesbuttons.command()
    async def bulk(self, ctx: commands.Context, message: discord.Message, *roles_buttons: RoleEmojiConverter):
        """Add a role-button to a message.
        """
        if not message.author == ctx.guild.me:
            await ctx.send(_("I have to be the author of the message for the role-button to work.").format(**locals()))
            return
        permissions = message.channel.permissions_for(ctx.guild.me)
        if not permissions.add_reactions or not permissions.read_message_history or not permissions.read_messages or not permissions.view_channel:
            await ctx.send(_("I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to see the messages in that channel.").format(**locals()))
            return
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if not f"{message.channel.id}-{message.id}" in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(roles_buttons) >= 25:
            await ctx.send(_("I can't do more than 25 roles-buttons for one message.").format(**locals()))
            return
        for role, button in roles_buttons:
            if hasattr(button, 'id'):
                config[f"{message.channel.id}-{message.id}"][f"{button.id}"] = {"role": role.id, "text_button": None}
            else:
                config[f"{message.channel.id}-{message.id}"][f"{button}"] = {"role": role.id, "text_button": None}
        try:
            await message.edit(components=self.get_buttons(config, message))
        except discord.HTTPException:
            await ctx.send(_("I can't do more than 25 roles-buttons for one message.").format(**locals()))
            return
        await self.config.guild(ctx.guild).roles_buttons.set(config)
        await ctx.tick()

    @rolesbuttons.command()
    async def remove(self, ctx: commands.Context, message: discord.Message, button: typing.Union[discord.Emoji, str]):
        """Remove a role-button to a message.
        """
        if not message.author == ctx.guild.me:
            await ctx.send(_("I have to be the author of the message for the role-button to work.").format(**locals()))
            return
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if not f"{message.channel.id}-{message.id}" in config:
            await ctx.send(_("No role-button is configured for this message.").format(**locals()))
            return
        if not f"{button}" in config[f"{message.channel.id}-{message.id}"]:
            await ctx.send(_("I wasn't watching for this button on this message.").format(**locals()))
            return
        del config[f"{message.channel.id}-{message.id}"][f"{button}"]
        await message.edit(components=self.get_buttons(config, message))
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).roles_buttons.set(config)
        await ctx.tick()

    @rolesbuttons.command()
    async def clear(self, ctx: commands.Context, message: discord.Message):
        """Clear all roles-buttons to a message.
        """
        if not message.author == ctx.guild.me:
            await ctx.send(_("I have to be the author of the message for the role-button to work.").format(**locals()))
            return
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if not f"{message.channel.id}-{message.id}" in config:
            await ctx.send(_("No role-button is configured for this message.").format(**locals()))
            return
        try:
            await message.edit(components=[])
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).roles_buttons.set(config)
        await ctx.tick()

    @rolesbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context):
        """Clear all roles-buttons to a **guild**.
        """
        await self.config.guild(ctx.guild).roles_buttons.clear()
        await ctx.tick()
    
    def get_buttons(self, config: typing.Dict, message: discord.Message):
        all_buttons = []
        lists = []
        one_l = [button for button in config[f"{message.channel.id}-{message.id}"]]
        while True:
            l = one_l[0:4]
            one_l = one_l[4:]
            lists.append(l)
            if one_l == []:
                break
        for l in lists:
            buttons = {"type": 1, "components": []}
            for button in l:
                try:
                    int(button)
                except ValueError:
                    buttons["components"].append({"type": 2, "style": 2, "label": config[f"{message.channel.id}-{message.id}"][f"{button}"]["text_button"], "emoji": {"name": f"{button}"}, "custom_id": f"roles_buttons {button}"})
                else:
                    buttons["components"].append({"type": 2, "style": 2, "label": config[f"{message.channel.id}-{message.id}"][f"{button}"]["text_button"], "emoji": {"name": f"{button}", "id": int(button)}, "custom_id": f"roles_buttons {button}"})
            all_buttons.append(ActionRow.from_dict(buttons))
        return all_buttons