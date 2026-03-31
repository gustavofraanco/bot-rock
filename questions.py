import json
import random
import os

PERGUNTAS_PATH = os.getenv("PERGUNTAS_JSON", "perguntas.json")
IMAGENS_PATH = os.getenv("IMAGENS_PATH", "imagens/")


def carregar_perguntas() -> list[dict]:
    """Carrega todas as perguntas do arquivo JSON."""
    with open(PERGUNTAS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def sortear_perguntas(quantidade: int) -> list[dict]:
    """
    Sorteia `quantidade` perguntas aleatórias sem repetição.
    Se pedir mais do que existe, retorna todas embaralhadas.
    """
    todas = carregar_perguntas()
    if quantidade >= len(todas):
        random.shuffle(todas)
        return todas
    return random.sample(todas, quantidade)


def get_caminho_imagem(nome_arquivo: str) -> str:
    """Retorna o caminho completo da imagem."""
    return os.path.join(IMAGENS_PATH, nome_arquivo)


def validar_resposta(resposta_usuario: str, resposta_correta: str) -> bool:
    """Valida a resposta do usuário (case insensitive, strip de espaços)."""
    return resposta_usuario.strip().lower() == resposta_correta.strip().lower()
