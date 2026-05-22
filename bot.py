import os
from pickle import FALSE

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.tree.sync()
    print("Bot is ready!")
    # testing 
    # for command in bot.tree.get_commands():
    #     print(f"Command: {command.name}")

async def global_command_check(interaction: discord.Interaction) -> bool:
    allowed_users = [721151215010054165]
    
    if interaction.type == discord.InteractionType.application_command:
        if interaction.user.id not in allowed_users:
            await interaction.response.send_message("go away")
            return False

    return True

bot.tree.interaction_check = global_command_check

@bot.tree.command(name="ping", description="Responds with Pong!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"{bot.latency * 1000:.2f} ms")

@bot.tree.context_menu(name="image")
async def image_context_menu(interaction: discord.Interaction, message: discord.Message):
    if not message.attachments:
        await interaction.response.send_message("No attachments found in the message.", ephemeral=True)
        return
    
    attachment = message.attachments[0]
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        await interaction.response.send_message("The attachment is not an image.", ephemeral=True)
        return
    
    await interaction.response.send_message(f"{attachment.url}", ephemeral=True)


if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))