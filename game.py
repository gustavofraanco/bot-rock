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
        """Calcula o tempo da rodada baseado na quantidade de jogadores ativos."""
        qtd = len(self.jogadores_ativos)
        if qtd >= 15:
            return 20
        elif 10 <= qtd < 15:
            return 13
        elif 5 <= qtd < 10:
            return 7
        else: # de 5 a 2 pessoas
            return 4

    @property
    def is_ultima_rodada(self) -> bool:
        return len(self.jogadores_ativos) == 2

    async def eliminar_jogador(self, jogador: discord.Member, motivo: str):
        """Remove o cargo @resta1, anuncia a eliminação e remove da lista."""
        try:
            await jogador.remove_roles(self.cargo_resta1)
        except discord.Forbidden:
            pass
        
        if jogador in self.jogadores_ativos:
            self.jogadores_ativos.remove(jogador)
            
        embed = discord.Embed(
            title="❌ Jogador Eliminado",
            description=f"{jogador.mention} foi eliminado!\n**Motivo:** {motivo}",
            color=discord.Color.red()
        )
        await self.canal.send(embed=embed)

    async def executar(self):
        """Loop principal da partida."""
        for i, pergunta in enumerate(self.perguntas):
            if not self.ativa or len(self.jogadores_ativos) <= 1:
                break

            self.rodada_atual = i + 1
            # Aplica a nova proporção de tempo solicitada
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
            return (
                m.channel == self.canal
                and m.author in self.jogadores_ativos
                and not m.author.bot
            )

        async def coletar():
            inicio = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - inicio < tempo:
                tempo_restante = tempo - (asyncio.get_event_loop().time() - inicio)
                try:
                    msg = await asyncio.wait_for(
                        self.bot.wait_for("message", check=check),
                        timeout=max(0, tempo_restante)
                    )
                    respostas[msg.author] = msg 

                    if validar_resposta(msg.content, resposta_correta):
                        if msg.author not in acertos_em_ordem:
                            acertos_em_ordem.append(msg.author)
                            try:
                                await msg.add_reaction(EMOJI_ACERTO)
                            except:
                                pass
                except asyncio.TimeoutError:
                    break

        await coletar()

        eliminados: list[tuple[discord.Member, str]] = []
        for jogador in list(self.jogadores_ativos):
            if jogador not in respostas:
                eliminados.append((jogador, "Não respondeu na rodada!"))
            elif not validar_resposta(respostas[jogador].content, resposta_correta):
                eliminados.append((jogador, "Respondeu incorretamente!"))

        todos_acertaram = (len(eliminados) == 0 and len(acertos_em_ordem) == len(self.jogadores_ativos))
        
        if todos_acertaram and acertos_em_ordem:
            ultimo_a_acertar = acertos_em_ordem[-1]
            eliminados.append((ultimo_a_acertar, "Foi o último a acertar quando todos acertaram!"))

        for jogador, motivo in eliminados:
            await self.eliminar_jogador(jogador, motivo)

    async def _rodar_ultima_rodada(self, pergunta: dict, tempo: int):
        jogadores_mencao = " ".join(j.mention for j in self.jogadores_ativos)
        resposta_correta = pergunta["resposta"]

        # Texto personalizado para a rodada final
        texto_final = (
            f"<:dale_info:1478237600908054548> **Acerte a imagem do tema Alemão**\n\n"
            f"<:dale_arco:1478415252868829274> Rodada **{self.rodada_atual} (FINAL)**\n"
            f"Tempo\n"
            f"<:fale_cronometro:1488631115001626785> **{tempo}**s\n\n"
            f"O primeiro a acertar vence!\n"
            f"{jogadores_mencao}"
        )

        embed_final = discord.Embed(description=texto_final, color=discord.Color.gold())
        caminho = get_caminho_imagem(pergunta["arquivo"])
        arquivo_discord = discord.File(caminho, filename=pergunta["arquivo"])
        embed_final.set_image(url=f"attachment://{pergunta['arquivo']}")
        
        await self.canal.send(file=arquivo_discord, embed=embed_final)

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
                    try: await msg.add_reaction(EMOJI_ACERTO)
                    except: pass
                    self.vencedor = msg.author
                    perdedor = [j for j in self.jogadores_ativos if j != self.vencedor][0]
                    await self.eliminar_jogador(perdedor, "Perdeu na rodada final!")
                    return
            except asyncio.TimeoutError:
                break

        if mensagens_enviadas:
            await self.eliminar_jogador(mensagens_enviadas[-1].author, "Tempo esgotado — último a responder sem acertar!")
        else:
            await self.eliminar_jogador(self.jogadores_ativos[0], "Ninguém respondeu na rodada final!")

        if self.jogadores_ativos:
            self.vencedor = self.jogadores_ativos[0]

    async def _enviar_embed_pergunta(self, pergunta: dict, tempo: int, mencoes: str):
        # Texto personalizado conforme solicitado
        texto_cabecalho = (
            f"<:dale_info:1478237600908054548> **Acerte a imagem do tema Alemão**\n\n"
            f"<:dale_arco:1478415252868829274> Rodada **{self.rodada_atual}**\n"
            f"Tempo\n"
            f"<:fale_cronometro:1488631115001626785> **{tempo}**s\n\n"
            f"{mencoes}"
        )

        embed = discord.Embed(
            description=texto_cabecalho,
            color=discord.Color.blue()
        )
        
        caminho = get_caminho_imagem(pergunta["arquivo"])
        arquivo_discord = discord.File(caminho, filename=pergunta["arquivo"])
        embed.set_image(url=f"attachment://{pergunta['arquivo']}")
        await self.canal.send(file=arquivo_discord, embed=embed)

    async def _encerrar(self):
        self.ativa = False
        if self.vencedor:
            embed = discord.Embed(
                title="🏆 TEMOS UM VENCEDOR!",
                description=f"Parabéns {self.vencedor.mention}! Você é o campeão do **Resta 1**! 🎉",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🏁 Partida Encerrada",
                description="A partida terminou sem vencedor.",
                color=discord.Color.greyple()
            )
        await self.canal.send(embed=embed)