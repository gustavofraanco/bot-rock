import asyncio
import json
import os
import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("MTQ4ODYwNjI4MzQ0MjQyMTc3MA.G5iu23.KPbT8jDEnO6eFyxeFaD8hPGlolJXIuHwAKighg")
CANAL_CDN_ID = int(os.getenv("1488885431083733132"))
PASTA_IMAGENS = "imagens"  # sua pasta com os .webp

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    canal = bot.get_channel(CANAL_CDN_ID)
    urls = {}

    # Carrega URLs já salvas (para retomar se interromper)
    if os.path.exists("urls.json"):
        with open("urls.json", "r") as f:
            urls = json.load(f)

    arquivos = [f for f in os.listdir(PASTA_IMAGENS) if f.endswith(".webp")]
    total = len(arquivos)

    for i, nome in enumerate(arquivos, 1):
        if nome in urls:
            print(f"[{i}/{total}] Já existe: {nome}")
            continue

        caminho = os.path.join(PASTA_IMAGENS, nome)
        try:
            msg = await canal.send(file=discord.File(caminho, filename=nome))
            urls[nome] = msg.attachments[0].url
            print(f"[{i}/{total}] ✅ {nome}")

            # Salva a cada upload (segurança contra interrupções)
            with open("urls.json", "w") as f:
                json.dump(urls, f, indent=2, ensure_ascii=False)

            await asyncio.sleep(0.5)  # evita rate limit
        except Exception as e:
            print(f"[{i}/{total}] ❌ Erro em {nome}: {e}")

    print("\n✅ Concluído! urls.json gerado.")
    await bot.close()

bot.run(TOKEN)