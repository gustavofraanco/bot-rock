import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from game import Partida

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_JOGO_ID = int(os.getenv("CANAL_JOGO_ID"))       # ID do canal exclusivo do jogo
CARGO_RESTA1_ID = int(os.getenv("CARGO_RESTA1_ID"))   # ID do cargo @resta1

# ── Intents ──────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Partida em andamento (apenas uma por vez)
partida_ativa: Partida | None = None


# ── Evento: bot pronto ────────────────────────────────────
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot online como {bot.user} | Comandos sincronizados.")


# ── Evento: mensagens durante a partida ──────────────────
@bot.event
async def on_message(message: discord.Message):
    global partida_ativa
    if message.author.bot:
        return
    if partida_ativa and partida_ativa.ativa:
        if message.channel.id == CANAL_JOGO_ID:
            partida_ativa.registrar_mensagem(message)
    await bot.process_commands(message)


# ── Comando /resta1 ───────────────────────────────────────
@tree.command(name="resta1", description="Inicia uma partida do Resta 1!")
@app_commands.describe(
    rodadas="Número de rodadas da partida",
    tempo_padrao="Tempo padrão por rodada em segundos (usado se a pergunta não tiver tempo próprio)"
)
async def resta1(interaction: discord.Interaction, rodadas: int, tempo_padrao: int = 30):
    global partida_ativa

    # Verifica se já há partida em andamento
    if partida_ativa and partida_ativa.ativa:
        await interaction.response.send_message(
            "⚠️ Já existe uma partida em andamento! Aguarde ela terminar.",
            ephemeral=True
        )
        return

    guild = interaction.guild
    canal_jogo = guild.get_channel(CANAL_JOGO_ID)
    cargo_resta1 = guild.get_role(CARGO_RESTA1_ID)

    if not canal_jogo:
        await interaction.response.send_message("❌ Canal do jogo não encontrado!", ephemeral=True)
        return
    if not cargo_resta1:
        await interaction.response.send_message("❌ Cargo @resta1 não encontrado!", ephemeral=True)
        return

    # Busca todos os membros com o cargo @resta1
    jogadores = [m for m in guild.members if cargo_resta1 in m.roles and not m.bot]

    if len(jogadores) < 2:
        await interaction.response.send_message(
            "❌ São necessários pelo menos **2 jogadores** com o cargo @resta1 para iniciar!",
            ephemeral=True
        )
        return

    if rodadas < 1:
        await interaction.response.send_message("❌ O número de rodadas deve ser pelo menos 1.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"✅ Partida iniciada com **{len(jogadores)} jogadores** e **{rodadas} rodadas**! "
        f"Vá para {canal_jogo.mention}!",
        ephemeral=False
    )

    # Anuncia início no canal do jogo
    mencoes = " ".join(j.mention for j in jogadores)
    embed_inicio = discord.Embed(
        title="🎮 RESTA 1 — A Partida Começou!",
        description=(
            f"**{len(jogadores)} jogadores** entrarão na arena!\n"
            f"A cada rodada, o **último a responder** é eliminado.\n"
            f"Na rodada final, o **primeiro a acertar** vence!\n\n"
            f"👥 Jogadores: {mencoes}"
        ),
        color=discord.Color.blurple()
    )
    await canal_jogo.send(embed=embed_inicio)

    # Cria e executa a partida
    partida_ativa = Partida(
        bot=bot,
        jogadores=jogadores,
        canal=canal_jogo,
        cargo_resta1=cargo_resta1,
        num_rodadas=rodadas,
        tempo_padrao=tempo_padrao
    )
    await partida_ativa.executar()
    partida_ativa = None  # Libera para nova partida


# ── Inicia o bot ──────────────────────────────────────────
bot.run(TOKEN)
