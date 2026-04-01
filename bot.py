import discord
from discord import app_commands
import os
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

    async def setup_hook(self):
        # Sincroniza os comandos com o Discord
        await self.tree.sync()

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user} | Comandos sincronizados.")

@bot.tree.command(name="resta1", description="Inicia uma partida de Resta 1")
async def resta1(interaction: discord.Interaction):
    """
    Comando para iniciar o jogo. 
    Usa defer() para evitar o erro 10062 (Unknown Interaction).
    """
    try:
        # 1. AVISO AO DISCORD: "Estou processando, não expire o comando!"
        await interaction.response.defer(ephemeral=False)

        # Configurações da partida (ajuste os IDs conforme seu servidor)
        ID_CANAL_JOGO = int(os.getenv("CANAL_JOGO_ID"))
        ID_CARGO_JOGADOR = int(os.getenv("CARGO_RESTA1_ID"))
        
        canal_jogo = bot.get_channel(ID_CANAL_JOGO)
        cargo_participante = interaction.guild.get_role(ID_CARGO_JOGADOR)

        if not canal_jogo or not cargo_participante:
            await interaction.followup.send("❌ Erro: Canal ou Cargo não encontrados. Verifique os IDs no bot.py.")
            return

        # Filtra os membros que possuem o cargo para iniciar a lista de jogadores
        jogadores = [m for m in interaction.guild.members if cargo_participante in m.roles and not m.bot]

        if len(jogadores) < 2:
            await interaction.followup.send(f"❌ Precisamos de pelo semos 2 jogadores com o cargo {cargo_participante.mention} para começar.")
            return

        # 2. INICIA A LÓGICA DA PARTIDA
        # Criamos a instância da Partida (que agora usa apenas imagens locais)
        nova_partida = Partida(
            bot=bot,
            jogadores=jogadores,
            canal=canal_jogo,
            cargo_resta1=cargo_participante,
            num_rodadas=len(jogadores),
            tempo_padrao=15
        )

        # 3. CONFIRMAÇÃO FINAL: Usamos followup.send porque já demos o defer()
        await interaction.followup.send(f"✅ Partida de **Resta 1** iniciada em {canal_jogo.mention}!")
        
        # Começa a execução do jogo
        await nova_partida.executar()

    except Exception as e:
        print(f"❌ Erro ao iniciar comando resta1: {e}")
        # Se der erro, tentamos avisar via followup
        try:
            await interaction.followup.send(f"⚠️ Ocorreu um erro ao tentar iniciar o jogo: {e}")
        except:
            pass

# Roda o bot
if __name__ == "__main__":
    bot.run(TOKEN)