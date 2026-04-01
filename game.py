import asyncio
import os
import discord
from questions import sortear_perguntas, get_caminho_imagem, validar_resposta

EMOJI_ACERTO = os.getenv("EMOJI_ACERTO", "✅")

class Partida:
    def __init__(self, bot: discord.Client, jogadores: list[discord.Member],
                 canal: discord.TextChannel, cargo_resta1: discord.Role,
                 num_rodadas: int, tempo_padrao: int):
        self.bot = bot
        self.jogadores_ativos: list[discord.Member] = list(jogadores)
        self.canal = canal
        self.cargo_resta1 = cargo_resta1
        self.tempo_padrao = tempo_padrao
        self.perguntas = sortear_perguntas(num_rodadas)
        self.rodada_atual = 0
        self.ativa = True
        self.vencedor: discord.Member | None = None

    def calcular_tempo_dinamico(self) -> int:
        qtd = len(self.jogadores_ativos)
        if qtd >= 15: return 20
        elif 10 <= qtd < 15: return 13
        elif 5 <= qtd < 10: return 7
        else: return 4

    @property
    def is_ultima_rodada(self) -> bool:
        return len(self.jogadores_ativos) == 2

    async def anunciar_inicio(self):
        """Embed de Início da Partida (#060606)"""
        mencoes = " ".join(j.mention for j in self.jogadores_ativos)
        embed = discord.Embed(
            description=(
                "# <:fale_restou:1488655051890233546> RESTA 1 - ALEMÃO\n"
                "ㅤ\n"
                "## <:gaale_regras:1488678788115075072> Instruções\n\n"
                "• A cada rodada, o **último a responder** é eliminado.\n"
                "• Na rodada final, o **primeiro a acertar** vence!\n\n"
                "<:fale_tempo:1488683795422122065> Inicia em **10** segundos...\n\n"
                f"{mencoes}"
            ),
            color=discord.Color(0x060606)
        )
        await self.canal.send(embed=embed)
        await asyncio.sleep(10)

    async def executar(self):
        await self.anunciar_inicio()
        
        for i, pergunta in enumerate(self.perguntas):
            if not self.ativa or len(self.jogadores_ativos) <= 1:
                break

            self.rodada_atual = i + 1
            tempo = self.calcular_tempo_dinamico()

            if self.is_ultima_rodada:
                await self._rodar_ultima_rodada(pergunta, tempo)
                break
            else:
                await self._rodar_rodada_normal(pergunta, tempo)

            if len(self.jogadores_ativos) == 1:
                self.vencedor = self.jogadores_ativos[0]
                break

        await self._encerrar()

    async def _rodar_rodada_normal(self, pergunta: dict, tempo: int):
        jogadores_mencao = " ".join(j.mention for j in self.jogadores_ativos)
        await self._enviar_embed_pergunta(pergunta, tempo, jogadores_mencao)

        resposta_correta = pergunta["resposta"]
        respostas: dict[discord.Member, discord.Message] = {}
        acertos_em_ordem: list[discord.Member] = []

        def check(m: discord.Message):
            return m.channel == self.canal and m.author in self.jogadores_ativos and not m.author.bot

        inicio = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - inicio < tempo:
            tempo_restante = tempo - (asyncio.get_event_loop().time() - inicio)
            try:
                msg = await asyncio.wait_for(self.bot.wait_for("message", check=check), timeout=max(0, tempo_restante))
                respostas[msg.author] = msg 
                if validar_resposta(msg.content, resposta_correta):
                    if msg.author not in acertos_em_ordem:
                        acertos_em_ordem.append(msg.author)
                        await msg.add_reaction(EMOJI_ACERTO)
            except asyncio.TimeoutError:
                break

        # Embed de Tempo Esgotado (#EB7309)
        await self.canal.send(embed=discord.Embed(description="<:fale_cronometro:1488631115001626785> **Acabou o tempo!**", color=0xEB7309))

        eliminados: list[discord.Member] = []
        for jogador in list(self.jogadores_ativos):
            if jogador not in acertos_em_ordem:
                eliminados.append(jogador)

        todos_acertaram = (len(eliminados) == 0 and len(acertos_em_ordem) == len(self.jogadores_ativos))
        if todos_acertaram and acertos_em_ordem:
            eliminados.append(acertos_em_ordem[-1])

        # Embed de Rodada Finalizada (#F1C40F)
        await self._anunciar_eliminados(pergunta["resposta"], eliminados)

    async def _rodar_ultima_rodada(self, pergunta: dict, tempo: int):
        jogadores_mencao = " ".join(j.mention for j in self.jogadores_ativos)
        await self._enviar_embed_pergunta(pergunta, tempo, jogadores_mencao, final=True)

        resposta_correta = pergunta["resposta"]
        mensagens_enviadas: list[discord.Message] = []

        def check(m: discord.Message):
            return m.channel == self.canal and m.author in self.jogadores_ativos and not m.author.bot

        inicio = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - inicio < tempo:
            tempo_restante = tempo - (asyncio.get_event_loop().time() - inicio)
            try:
                msg = await asyncio.wait_for(self.bot.wait_for("message", check=check), timeout=max(0, tempo_restante))
                mensagens_enviadas.append(msg)
                if validar_resposta(msg.content, resposta_correta):
                    await msg.add_reaction(EMOJI_ACERTO)
                    self.vencedor = msg.author
                    perdedor = [j for j in self.jogadores_ativos if j != self.vencedor][0]
                    await self.canal.send(embed=discord.Embed(description="<:fale_cronometro:1488631115001626785> **Acabou o tempo!**", color=0xEB7309))
                    await self._anunciar_eliminados(pergunta["resposta"], [perdedor])
                    return
            except asyncio.TimeoutError:
                break

        await self.canal.send(embed=discord.Embed(description="<:fale_cronometro:1488631115001626785> **Acabou o tempo!**", color=0xEB7309))
        eliminado = mensagens_enviadas[-1].author if mensagens_enviadas else self.jogadores_ativos[0]
        await self._anunciar_eliminados(pergunta["resposta"], [eliminado])
        if self.jogadores_ativos: self.vencedor = self.jogadores_ativos[0]

    async def _enviar_embed_pergunta(self, pergunta: dict, tempo: int, mencoes: str, final=False):
        rodada_str = f"**{self.rodada_atual} (FINAL)**" if final else f"**{self.rodada_atual}**"
        embed = discord.Embed(
            description=(
                "# <:dale_info:1478237600908054548> ACERTE A IMAGEM\n"
                "ㅤ\n"
                "Rodada\n"
                f"<:fale_rodada:1488649428989382987> {rodada_str}\n"
                "Tempo\n"
                f"<:fale_cronometro:1488631115001626785> **{tempo}**s\n\n"
                f"{mencoes}"
            ),
            color=0x060606
        )
        caminho = get_caminho_imagem(pergunta["arquivo"])
        file = discord.File(caminho, filename=pergunta["arquivo"])
        embed.set_image(url=f"attachment://{pergunta['arquivo']}")
        await self.canal.send(file=file, embed=embed)

    async def _anunciar_eliminados(self, resposta, eliminados):
        for j in eliminados:
            if j in self.jogadores_ativos: self.jogadores_ativos.remove(j)
            try: await j.remove_roles(self.cargo_resta1)
            except: pass

        lista_eliminados = "\n".join([f"<:dale_errado:1488652581428527125> {j.mention}" for j in eliminados])
        embed = discord.Embed(
            description=(
                "# <:fale_finalizada:1488692025984553241> Rodada finalizada!\n"
                f"• A resposta era `{resposta}`\n"
                "Jogador(es) eliminado(os):\n"
                f"{lista_eliminados}"
            ),
            color=0xF1C40F
        )
        embed.set_footer(text=f"Restam {len(self.jogadores_ativos)} jogadores")
        await self.canal.send(embed=embed)

    async def _encerrar(self):
        self.ativa = False
        if self.vencedor:
            embed = discord.Embed(
                description=(
                    "# <:fale_vencedor:1488653915464663060> Resta apenas 1!\n"
                    f"Parabéns, {self.vencedor.mention}! Você é o **último restante** no jogo. <:dale_eventos:1478383216581672982>"
                ),
                color=0x870606
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1475457661842751548/1488696064579076157/IMG_9600.png?ex=69cdb7c0&is=69cc6640&hm=49e2a616a13482ebc95a0d1edd44a1ed4d14a7574dce86e7e7272a855753b107&=&format=webp&quality=lossless")
            await self.canal.send(embed=embed)