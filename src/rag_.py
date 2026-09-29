from sentence_transformers import SentenceTransformer
from google import genai
import chromadb


from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = PASTA_PROJETO / "banco"

COLECAO = "documentos"
MODELO_EMBEDDING = "all-MiniLM-L6-v2"
MODELO_GEMINI = "gemini-3.5-flash-lite"


print("Carregando modelo de embeddings...")

modelo_embedding = SentenceTransformer(MODELO_EMBEDDING)

print("Conectando ao ChromaDB...")

cliente_chroma = chromadb.PersistentClient(
    path=CAMINHO_BANCO
)

colecao = cliente_chroma.get_collection(
    name=COLECAO
)

print("Conectando ao Gemini...")

cliente_gemini = genai.Client()

print("\n" + "=" * 70)
print("RAG iniciado!")
print("Digite sua pergunta.")
print("Digite 'sair' para encerrar.")
print("=" * 70)


while True:

    pergunta = input("\nPergunta: ").strip()

    if pergunta.lower() in ["sair", "exit", "quit"]:
        print("\nEncerrando o RAG...")
        break

    if not pergunta:
        continue

    vetor_pergunta = modelo_embedding.encode(
        pergunta
    ).tolist()

    resultado = colecao.query(
        query_embeddings=[vetor_pergunta],
        n_results=5
    )

    contexto = ""

    for i, documento in enumerate(resultado["documents"][0]):

        pagina = resultado["metadatas"][0][i]["pagina"]

        contexto += f"""
--- TRECHO {i + 1} ---
Página: {pagina}

{documento}

"""

    prompt = f"""
Você é um assistente técnico especializado em automação industrial.

Responda à pergunta utilizando SOMENTE as informações presentes
nos trechos do manual fornecidos abaixo.

Se a informação não estiver presente nos trechos, diga claramente:

"Não encontrei essa informação no manual."

Não invente informações.

Sempre que possível, informe a página do manual onde encontrou
a informação.

PERGUNTA:
{pergunta}

TRECHOS DO MANUAL:
{contexto}
"""

    print("\nConsultando Gemini...")

    try:

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

        print("\nERRO AO CONSULTAR O GEMINI:")
        print(erro)
