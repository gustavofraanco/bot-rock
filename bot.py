import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from game import Partida

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_JOGO_ID = int(os.getenv("CANAL_JOGO_ID"))
CARGO_RESTA1_ID = int(os.getenv("CARGO_RESTA1_ID"))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

partida_ativa: Partida | None = None

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot online como {bot.user} | Comandos sincronizados.")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)

# ── Comando Iniciar ───────────────────────────────────────
@tree.command(name="resta1", description="Inicia uma partida do Resta 1!")
async def resta1(interaction: discord.Interaction, rodadas: int, tempo_padrao: int = 30):
    global partida_ativa

    if partida_ativa and partida_ativa.ativa:
        await interaction.response.send_message("⚠️ Já existe uma partida em andamento!", ephemeral=True)
        return

    guild = interaction.guild
    canal_jogo = guild.get_channel(CANAL_JOGO_ID)
    cargo_resta1 = guild.get_role(CARGO_RESTA1_ID)

    jogadores = [m for m in guild.members if cargo_resta1 in m.roles and not m.bot]

    if len(jogadores) < 2:
        await interaction.response.send_message("❌ Mínimo de 2 jogadores com o cargo necessário!", ephemeral=True)
        return

    await interaction.response.send_message(f"✅ Partida iniciada em {canal_jogo.mention}!", ephemeral=False)

    partida_ativa = Partida(bot, jogadores, canal_jogo, cargo_resta1, rodadas, tempo_padrao)
    try:
        await partida_ativa.executar()
    finally:
        partida_ativa = None

# ── Comando Finalizar ──────────────────────────────────────
@tree.command(name="finalizar", description="Para a partida atual imediatamente.")
@app_commands.checks.has_permissions(administrator=True)
async def finalizar(interaction: discord.Interaction):
    global partida_ativa

    if not partida_ativa or not partida_ativa.ativa:
        await interaction.response.send_message("❌ Não há partida ativa para finalizar.", ephemeral=True)
        return

    partida_ativa.finalizar_forcado()
    await interaction.response.send_message("🛑 Partida finalizada manualmente por um administrador.", ephemeral=False)
    partida_ativa = None

bot.run(TOKEN)