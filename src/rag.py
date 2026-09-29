from pathlib import Path
from google import genai
import sys
import os

# Força o console do Windows a usar UTF-8 para evitar erros com caracteres especiais (ex: ≥, —)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Importa a função de busca avançada do arquivo busca.py
from busca import buscar

# ============================================================
# CONFIGURAÇÕES
# ============================================================

MODELO_GEMINI = "gemini-3.6-flash"  # Ajuste conforme o modelo ativo na sua API

print("Conectando ao Gemini...")
cliente_gemini = genai.Client()

print("\n" + "=" * 70)
print("RAG - CONSULTA AOS MANUAIS")
print("Digite sua pergunta.")
print("Digite 'sair' para encerrar.")
print("=" * 70)


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

if __name__ == "__main__":

    while True:

        pergunta = input("\nPergunta: ").strip()

        if pergunta.lower() in ["sair", "exit", "quit"]:
            print("\nEncerrando o RAG...")
            break

        if not pergunta:
            continue

        try:
            # Executa a busca silenciando temporariamente os prints internos do busca.py
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
            try:
                resultados = buscar(pergunta)
            finally:
                sys.stdout.close()
                sys.stdout = sys.__stdout__

            if not resultados:
                print("\n" + "=" * 70)
                print("RESPOSTA")
                print("=" * 70)
                print("Não encontrei essa informação no manual.")
                print("=" * 70)
                continue

            # Monta o contexto utilizando os melhores trechos retornados (Top 5)
            contexto = ""

            for i, res in enumerate(resultados[:5]):
                metadata = res["metadata"]
                pagina = metadata.get("pagina", "N/A")
                arquivo = metadata.get("arquivo", "N/A")
                documento = res["texto"]

                contexto += f"""
--- TRECHO {i + 1} ---
Arquivo: {arquivo} | Página: {pagina}

{documento}
"""

            # Constrói o prompt para o Gemini
            prompt = f"""
Você é um assistente técnico especializado em automação industrial.

Responda à pergunta utilizando SOMENTE as informações presentes
nos trechos do manual fornecidos abaixo.

Se a informação não estiver presente nos trechos, diga claramente:

"Não encontrei essa informação no manual."

Não invente informações.

Sempre que possível, informe a página e o arquivo do manual onde encontrou
a informação.

PERGUNTA:
{pergunta}

TRECHOS DO MANUAL:
{contexto}
"""

            print("\nConsultando Gemini...")

            resposta = cliente_gemini.interactions.create(
                model=MODELO_GEMINI,
                input=prompt
            )

            print("\n" + "=" * 70)
            print("RESPOSTA")
            print("=" * 70)

            print(resposta.output_text)

            print("=" * 70)

        except Exception as erro:

            # Garante que o stdout seja restaurado caso ocorra algum erro
            sys.stdout = sys.__stdout__

            print("\n" + "=" * 70)
            print("ERRO AO PROCESSAR A PERGUNTA:")
            print("=" * 70)
            print(erro)
            print("=" * 70)