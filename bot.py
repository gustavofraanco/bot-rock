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
    # O on_message agora só processa comandos prefixados. 
    # A lógica de capturar respostas está dentro do game.py usando wait_for.
    if message.author.bot:
        return
    await bot.process_commands(message)

@tree.command(name="resta1", description="Inicia uma partida do Resta 1!")
@app_commands.describe(
    rodadas="Número de rodadas da partida",
    tempo_padrao="Tempo padrão por rodada em segundos"
)
async def resta1(interaction: discord.Interaction, rodadas: int, tempo_padrao: int = 30):
    global partida_ativa

    if partida_ativa and partida_ativa.ativa:
        await interaction.response.send_message(
            "⚠️ Já existe uma partida em andamento! Aguarde ela terminar.",
            ephemeral=True
        )
        return

    guild = interaction.guild
    canal_jogo = guild.get_channel(CANAL_JOGO_ID)
    cargo_resta1 = guild.get_role(CARGO_RESTA1_ID)

    if not canal_jogo or not cargo_resta1:
        await interaction.response.send_message("❌ Canal ou Cargo não encontrados!", ephemeral=True)
        return

    jogadores = [m for m in guild.members if cargo_resta1 in m.roles and not m.bot]

    if len(jogadores) < 2:
        await interaction.response.send_message(
            f"❌ São necessários pelo menos **2 jogadores** com o cargo @resta1!",
            ephemeral=True
        )
        return

    # Mensagem de confirmação apenas para quem usou o comando
    await interaction.response.send_message(
        f"✅ Partida de **Resta 1** iniciada em {canal_jogo.mention}!",
        ephemeral=False
    )

    # AQUI ESTAVA O ERRO: O embed azul foi removido totalmente.
    
    partida_ativa = Partida(
        bot=bot,
        jogadores=jogadores,
        canal=canal_jogo,
        cargo_resta1=cargo_resta1,
        num_rodadas=rodadas,
        tempo_padrao=tempo_padrao
    )
    
    try:
        await partida_ativa.executar()
    finally:
        partida_ativa = None

bot.run(TOKEN)