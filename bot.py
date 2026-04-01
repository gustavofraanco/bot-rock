import discord
from discord import app_commands
import os
import time
from dotenv import load_dotenv
from game import Partida

# Carrega as variáveis do arquivo .env
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Configuração de Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.partida_atual = None  # Para podermos finalizar a partida depois

    async def setup_hook(self):
        # Sincroniza os comandos com o Discord
        await self.tree.sync()

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user} | Comandos sincronizados.")

@bot.tree.command(name="resta1", description="Inicia uma partida de Resta 1")
async def resta1(interaction: discord.Interaction):
    """Inicia o jogo usando defer para evitar erro 10062."""
    await interaction.response.defer(ephemeral=False)

    try:
        # Puxa os IDs direto do seu .env (Nomes devem estar iguais aos do arquivo)
        ID_CANAL_JOGO = int(os.getenv("CANAL_JOGO_ID"))
        ID_CARGO_JOGADOR = int(os.getenv("CARGO_RESTA1_ID"))
        
        canal_jogo = bot.get_channel(ID_CANAL_JOGO)
        cargo_participante = interaction.guild.get_role(ID_CARGO_JOGADOR)

        if not canal_jogo or not cargo_participante:
            await interaction.followup.send("❌ Erro: Verifique os IDs de Canal e Cargo no seu arquivo .env")
            return

        # Filtra os membros com o cargo
        jogadores = [m for m in interaction.guild.members if cargo_participante in m.roles and not m.bot]

        if len(jogadores) < 2:
            await interaction.followup.send(f"❌ Mínimo de 2 jogadores com o cargo {cargo_participante.mention} para começar.")
            return

        # Inicia a instância da Partida
        bot.partida_atual = Partida(
            bot=bot,
            jogadores=jogadores,
            canal=canal_jogo,
            cargo_resta1=cargo_participante,
            num_rodadas=len(jogadores),
            tempo_padrao=15
        )

        await interaction.followup.send(f"✅ Partida iniciada em {canal_jogo.mention}!")
        
        # Executa o loop do jogo
        await bot.partida_atual.executar()

    except Exception as e:
        print(f"❌ Erro no comando resta1: {e}")
        try:
            await interaction.followup.send(f"⚠️ Erro ao iniciar: {e}")
        except:
            pass

@bot.tree.command(name="finalizar", description="Finaliza a partida atual imediatamente")
async def finalizar(interaction: discord.Interaction):
    """Interrompe a partida que está acontecendo."""
    if bot.partida_atual and bot.partida_atual.ativa:
        bot.partida_atual.finalizar_forcado()
        await interaction.response.send_message("🛑 A partida foi finalizada manualmente!", ephemeral=False)
        bot.partida_atual = None
    else:
        await interaction.response.send_message("❌ Não há nenhuma partida rodando no momento.", ephemeral=True)

# Execução principal
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERRO: Variável TOKEN não encontrada. Verifique seu .env")
    else:
        bot.run(TOKEN)