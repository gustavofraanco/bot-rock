# 🎮 Resta 1 — Bot Discord

Bot de jogo para Discord onde o último a responder é eliminado a cada rodada, e o primeiro a acertar na rodada final vence.

---

## 📁 Estrutura de Pastas

```
resta1_bot/
├── bot.py              # Código principal do bot
├── game.py             # Lógica da partida
├── questions.py        # Gerenciador do banco de perguntas
├── perguntas.json      # Banco de dados das perguntas
├── requirements.txt    # Dependências Python
├── .env.example        # Modelo das variáveis de ambiente
└── imagens/            # Pasta com as imagens .webp
    ├── pergunta1.webp
    ├── pergunta2.webp
    └── ...
```

---

## ⚙️ Configuração Inicial

### 1. Portal do Discord Developer

1. Acesse https://discord.com/developers/applications
2. Crie uma **New Application** e vá em **Bot**
3. Copie o **Token** do bot
4. Em **Privileged Gateway Intents**, ative:
   - `SERVER MEMBERS INTENT`
   - `MESSAGE CONTENT INTENT`
5. Em **OAuth2 > URL Generator**, selecione:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Manage Roles`, `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`
6. Use a URL gerada para convidar o bot ao servidor

### 2. No seu servidor Discord

- Crie o cargo `@resta1` e dê-o a todos os participantes
- Crie um canal exclusivo para o jogo (ex: `#resta1-arena`)
- Copie os IDs do cargo e do canal (clique com botão direito com Modo Desenvolvedor ativado)

### 3. Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha:

```env
DISCORD_TOKEN=seu_token_aqui
CANAL_JOGO_ID=ID_do_canal_do_jogo
CARGO_RESTA1_ID=ID_do_cargo_resta1
```

### 4. Banco de Perguntas

Edite `perguntas.json` seguindo o formato:

```json
[
  {
    "arquivo": "nome_da_imagem.webp",
    "enunciado": "Texto da pergunta exibido no embed",
    "resposta": "resposta correta",
    "tempo": 30
  }
]
```

Coloque as imagens `.webp` na pasta `imagens/`.

---

## ▶️ Rodando Localmente

```bash
pip install -r requirements.txt
python bot.py
```

---

## 🚀 Deploy no Railway

1. Suba o projeto para um repositório GitHub
2. No Railway, crie um novo projeto a partir do repositório
3. Em **Variables**, adicione as mesmas variáveis do `.env`
4. O Railway detectará automaticamente o Python e executará `bot.py`

> ⚠️ As imagens `.webp` e o `perguntas.json` precisam estar commitados no repositório ou em um volume persistente no Railway.

---

## 🎮 Como Jogar

1. Use o comando `/resta1 rodadas:<número> tempo_padrao:<segundos>` em qualquer canal
2. Todos com o cargo `@resta1` entram automaticamente
3. A cada rodada, uma pergunta é sorteada aleatoriamente do banco
4. O **último jogador a enviar uma mensagem** no canal do jogo é eliminado
5. Na rodada final (2 jogadores), o **primeiro a responder corretamente** vence
6. O eliminado perde o cargo `@resta1`

---

## 📝 Regras

| Situação | Resultado |
|---|---|
| Rodada normal | Último a responder é eliminado |
| Ninguém responde | Primeiro da lista é eliminado |
| Rodada final | Primeiro a acertar vence; o outro é eliminado |
| Rodada final sem acerto | Último a responder é eliminado |
