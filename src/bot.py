import discord
import re
import traceback
import os
from dotenv import load_dotenv
import random
import asyncio

load_dotenv()

ADD_CHANNEL_ID = 1186225608494153858
TESTED_CHANNEL_ID = 1186225617398673408
BAD_SITES_CHANNEL_ID = 1186228213047898142
URL_PATTERN = re.compile(r"https?://\S+")
MOD_ROLE_ID = 1186217822951579698

COLORS = [0x00C3F4, 0xAF416F]


class Options(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Discuss",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:discuss",
    )
    async def discuss(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        embed = interaction.message.embeds[0]
        url_field_value = embed.fields[0].value

        match = URL_PATTERN.search(url_field_value)
        link = match.group()

        await interaction.message.create_thread(name=link)
        button.disabled = True
        button.label = "Thread Open"
        await interaction.message.edit(view=self)
        await interaction.response.defer()

    @discord.ui.button(
        label="Move to Tested",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:test",
    )
    async def test(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        url_field_value = embed.fields[0].value

        match = URL_PATTERN.search(url_field_value)
        link = match.group()

        thread = interaction.guild.get_thread(interaction.message.id)
        view = TestModal(link=link, thread=thread if thread else None)
        await interaction.response.send_modal(view)
        await view.wait()

    @discord.ui.button(
        label="Remove",
        style=discord.ButtonStyle.red,
        custom_id="persistent_view:remove",
    )
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        url_field_value = embed.fields[0].value

        match = URL_PATTERN.search(url_field_value)
        link = match.group()

        thread = interaction.guild.get_thread(interaction.message.id)
        view = RemovalReason(link=link, thread=thread if thread else None)
        await interaction.response.send_modal(view)
        await view.wait()

        await interaction.message.delete()


class TestModal(discord.ui.Modal):
    def __init__(self, link, thread):
        super().__init__(title="Test Link", timeout=None)
        self.link = link
        self.thread = thread

    link_title = discord.ui.TextInput(
        label="Link Title",
        placeholder="e.g. DuckDuckGo",
    )

    link_description = discord.ui.TextInput(
        label="Link Description",
        style=discord.TextStyle.long,
        placeholder="e.g. Privacy Focused Search Engine",
        required=False,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        TESTED_CHANNEL = interaction.guild.get_channel(TESTED_CHANNEL_ID)
        embed = discord.Embed(
            title=f"\\* \\[{self.link_title}](<{self.link}>) - {self.link_description}"
        )
        embed.add_field(
            name="",
            value=f"Discussion: {self.thread.mention}" if self.thread else "",
            inline=False,
        )
        embed.set_footer(text=f"Tested by {interaction.user}")
        msg = await TESTED_CHANNEL.send(embed=embed)
        # if not self.thread
        await interaction.response.send_message(
            f"Tested link sent! {msg.jump_url}", ephemeral=True
        )
        await interaction.message.delete()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        await interaction.response.send_message(
            "Oops! Something went wrong. Please try again later or notify @snowz.nz.",
            ephemeral=True,
        )

        traceback.print_exception(type(error), error, error.__traceback__)


class RemovalReason(discord.ui.Modal):
    def __init__(self, link, thread):
        super().__init__(title="Remove Link", timeout=None)
        self.link = link
        self.thread = thread

    reason = discord.ui.TextInput(
        label="Reason for removal",
        style=discord.TextStyle.long,
        placeholder="e.g. Malicious",
        required=True,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        BAD_CHANNEL = interaction.guild.get_channel(BAD_SITES_CHANNEL_ID)
        embed = discord.Embed(title=self.link)
        embed.add_field(
            name=self.reason,
            value=f"Discussion: {self.thread.mention}" if self.thread else "",
            inline=False,
        )
        embed.set_footer(text=f"Removed by {interaction.user}")
        msg = await BAD_CHANNEL.send(embed=embed)
        await msg.add_reaction("🔼")
        await msg.add_reaction("🔽")
        await interaction.response.send_message(
            f"Removal reason sent! {msg.jump_url}", ephemeral=True
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        await interaction.response.send_message(
            "Oops! Something went wrong. Please try again later or notify @snowz.nz.",
            ephemeral=True,
        )

        traceback.print_exception(type(error), error, error.__traceback__)


class Client(discord.Client):
    async def setup_hook(self) -> None:
        self.add_view(Options())

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user}")

    async def on_message(self, message) -> None:
        if message.author == self.user:
            return
        if message.author.bot:
            return
        if message.channel.id == ADD_CHANNEL_ID:
            urls = URL_PATTERN.findall(message.content)
            if urls:
                await message.delete()
                for url in urls:
                    embed = discord.Embed(color=random.choice(COLORS))
                    embed.add_field(name="", value=f"{url}", inline=False)
                    embed.set_footer(text=f"Submitted by {message.author}")
                    msg = await message.channel.send(embed=embed, view=Options())
                    await msg.add_reaction("🔼")
                    await msg.add_reaction("🔽")
            else:
                await message.delete()
                embed = discord.Embed(color=0xED4245)
                embed.add_field(
                    name="",
                    value=f"Your message must contain a URL! {message.author.mention}",
                    inline=False,
                )
                msg = await message.channel.send(embed=embed)
                await asyncio.sleep(3)
                await msg.delete()


intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = Client(
    intents=intents,
    activity=discord.Activity(name="links!", type=discord.ActivityType.watching),
)


client.run(os.getenv("DISCORD_BOT_TOKEN"))
