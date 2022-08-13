import re
from typing import Dict, Optional, Sequence, Union

import discord
from discord.ext import commands


def role_mention_cleanup(message: discord.Message, cogsutils) -> Union[str, None]:
    content = message.content
    if not content:
        return None
    assert isinstance(content, str), "Message.content got screwed somehow..."  # nosec
    if message.guild is None:
        return content
    transformations = {
        re.escape("<@&{0.id}>".format(role)): "@" + role.name
        for role in message.role_mentions
    }
    def repl(obj):
        return transformations.get(re.escape(obj.group(0)), "")
    pattern = re.compile("|".join(transformations.keys()))
    result = pattern.sub(repl, content)
    return result

def embed_from_msg(message: discord.Message, cogsutils) -> discord.Embed:
    channel = message.channel
    assert isinstance(channel, discord.TextChannel), "mypy"  # nosec
    guild = channel.guild
    content = role_mention_cleanup(message, cogsutils)
    author = message.author
    avatar = author.display_avatar if cogsutils.is_dpy2 else author.avatar_url
    footer = f"Said in {guild.name} #{channel.name}"

    try:
        color = author.color if author.color.value != 0 else None
    except AttributeError:  # happens if message author not in guild anymore.
        color = None
    em = discord.Embed(description=content, timestamp=message.created_at)
    if color:
        em.color = color

    em.set_author(name=f"{author.name}", icon_url=avatar)
    em.set_footer(icon_url=guild.icon or "" if cogsutils.is_dpy2 else guild.icon_url or "", text=footer)
    if message.attachments:
        a = message.attachments[0]
        fname = a.filename
        url = a.url
        if fname.split(".")[-1] in ["png", "jpg", "gif", "jpeg"]:
            em.set_image(url=url)
        else:
            em.add_field(
                name="Message has an attachment", value=f"[{fname}]({url})", inline=True
            )
    return em