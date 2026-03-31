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

    @property
    def is_ultima_rodada(self) -> bool:
        return len(self.jogadores_ativos) == 2

    async def eliminar_jogador(self, jogador: discord.Member, motivo: str):
        """Remove o cargo @resta1, anuncia a eliminação e remove da lista."""
        try:
            await jogador.remove_roles(self.cargo_resta1)
        except discord.Forbidden:
            pass
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
            tempo = pergunta.get("tempo", self.tempo_padrao)

            if self.is_ultima_rodada:
                await self._rodar_ultima_rodada(pergunta, tempo)
                break
            else:
                await self._rodar_rodada_normal(pergunta, tempo)

            # Checa se restou apenas 1 jogador após a rodada
            if len(self.jogadores_ativos) == 1:
                self.vencedor = self.jogadores_ativos[0]
                break

        await self._encerrar()

    # ─────────────────────────────────────────────────────────────
    # RODADA NORMAL
    # ─────────────────────────────────────────────────────────────
    async def _rodar_rodada_normal(self, pergunta: dict, tempo: int):
        """
        Lógica de eliminação:
        1. Quem não respondeu nada → eliminado
        2. Quem respondeu errado → eliminado
        3. Se TODOS acertaram → o último a acertar também é eliminado
        4. Se pelo menos 1 errou/silenciou → quem acertou sobrevive
        """
        jogadores_mencao = " ".join(j.mention for j in self.jogadores_ativos)
        await self._enviar_embed_pergunta(pergunta, tempo, jogadores_mencao)

        resposta_correta = pergunta["resposta"]

        # última mensagem de cada jogador
        respostas: dict[discord.Member, discord.Message] = {}
        # quem acertou, em ordem cronológica (apenas primeiro acerto de cada um)
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
                        timeout=tempo_restante
                    )
                    respostas[msg.author] = msg  # sobrescreve com a mais recente

                    # Reage com emoji se acertou (apenas primeira vez)
                    if validar_resposta(msg.content, resposta_correta):
                        if msg.author not in acertos_em_ordem:
                            acertos_em_ordem.append(msg.author)
                            try:
                                await msg.add_reaction(EMOJI_ACERTO)
                            except discord.HTTPException:
                                pass
                except asyncio.TimeoutError:
                    break

        await coletar()

        # ── Determina eliminados ──────────────────────────────────
        eliminados: list[tuple[discord.Member, str]] = []

        for jogador in list(self.jogadores_ativos):
            if jogador not in respostas:
                eliminados.append((jogador, "Não respondeu na rodada!"))
            elif not validar_resposta(respostas[jogador].content, resposta_correta):
                eliminados.append((jogador, "Respondeu incorretamente!"))

        # Se TODOS acertaram → o último a acertar é eliminado também
        todos_acertaram = (
            len(eliminados) == 0
            and len(acertos_em_ordem) == len(self.jogadores_ativos)
        )
        if todos_acertaram and acertos_em_ordem:
            ultimo_a_acertar = acertos_em_ordem[-1]
            eliminados.append((ultimo_a_acertar, "Foi o último a acertar quando todos acertaram!"))

        # Aplica eliminações
        for jogador, motivo in eliminados:
            if jogador in self.jogadores_ativos:
                await self.eliminar_jogador(jogador, motivo)

    # ─────────────────────────────────────────────────────────────
    # RODADA FINAL (2 jogadores)
    # ─────────────────────────────────────────────────────────────
    async def _rodar_ultima_rodada(self, pergunta: dict, tempo: int):
        """
        Rodada final:
        - Vence o PRIMEIRO a responder corretamente.
        - O outro é eliminado.
        - Se ninguém acertar no tempo → o último a responder qualquer coisa é eliminado.
        - Se ninguém respondeu nada → elimina o primeiro da lista.
        """
        jogadores_mencao = " ".join(j.mention for j in self.jogadores_ativos)
        resposta_correta = pergunta["resposta"]

        embed_final = discord.Embed(
            title="🏆 RODADA FINAL — Resta 1!",
            description=(
                f"**{pergunta['enunciado']}**\n\n"
                f"⏱️ Tempo: **{tempo}s**\n"
                f"O **primeiro a acertar** vence!\n\n"
                f"{jogadores_mencao}"
            ),
            color=discord.Color.gold()
        )
        caminho = get_caminho_imagem(pergunta["arquivo"])
        arquivo_discord = discord.File(caminho, filename=pergunta["arquivo"])
        embed_final.set_image(url=f"attachment://{pergunta['arquivo']}")
        await self.canal.send(file=arquivo_discord, embed=embed_final)

        mensagens_enviadas: list[discord.Message] = []

        def check(m: discord.Message):
            return (
                m.channel == self.canal
                and m.author in self.jogadores_ativos
                and not m.author.bot
            )

        inicio = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - inicio < tempo:
            tempo_restante = tempo - (asyncio.get_event_loop().time() - inicio)
            try:
                msg = await asyncio.wait_for(
                    self.bot.wait_for("message", check=check),
                    timeout=tempo_restante
                )
                mensagens_enviadas.append(msg)

                if validar_resposta(msg.content, resposta_correta):
                    try:
                        await msg.add_reaction(EMOJI_ACERTO)
                    except discord.HTTPException:
                        pass
                    self.vencedor = msg.author
                    perdedor = [j for j in self.jogadores_ativos if j != self.vencedor][0]
                    await self.eliminar_jogador(perdedor, "Perdeu na rodada final!")
                    return

            except asyncio.TimeoutError:
                break

        # Tempo esgotado sem acerto
        if mensagens_enviadas:
            eliminado = mensagens_enviadas[-1].author
            await self.eliminar_jogador(eliminado, "Tempo esgotado — foi o último a responder sem acertar!")
        else:
            await self.eliminar_jogador(self.jogadores_ativos[0], "Ninguém respondeu na rodada final!")

        if self.jogadores_ativos:
            self.vencedor = self.jogadores_ativos[0]

    # ─────────────────────────────────────────────────────────────
    # EMBED DE PERGUNTA NORMAL
    # ─────────────────────────────────────────────────────────────
    async def _enviar_embed_pergunta(self, pergunta: dict, tempo: int, mencoes: str):
        embed = discord.Embed(
            title=f"📋 Rodada {self.rodada_atual}",
            description=(
                f"**{pergunta['enunciado']}**\n\n"
                f"⏱️ Tempo: **{tempo}s**\n"
                f"Quem **não acertar** ou for o **último a acertar** (se todos acertarem) será eliminado!\n\n"
                f"{mencoes}"
            ),
            color=discord.Color.blue()
        )
        caminho = get_caminho_imagem(pergunta["arquivo"])
        arquivo_discord = discord.File(caminho, filename=pergunta["arquivo"])
        embed.set_image(url=f"attachment://{pergunta['arquivo']}")
        await self.canal.send(file=arquivo_discord, embed=embed)

    # ─────────────────────────────────────────────────────────────
    # ENCERRAMENTO
    # ─────────────────────────────────────────────────────────────
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
