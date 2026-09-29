from pathlib import Path
import hashlib

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from sentence_transformers import SentenceTransformer
import chromadb


# ============================================================
# CONFIGURAÇÃO
# ============================================================

PASTA_PROJETO = Path(__file__).resolve().parent.parent
PASTA_DOCUMENTOS = PASTA_PROJETO / "documentos"
PASTA_BANCO = PASTA_PROJETO / "banco"

NOME_COLECAO = "documentos"

TAMANHO_CHUNK = 1000
OVERLAP_CHUNK = 150


# ============================================================
# IDENTIFICAÇÃO DE FAMÍLIA E MODELO
# ============================================================

def identificar_equipamento(nome_arquivo):
    """
    Identifica família e modelo a partir do nome do arquivo.

    Esta função foi feita para ser expandida posteriormente
    conforme novos fabricantes/equipamentos forem adicionados.
    """

    nome = nome_arquivo.upper()

    familia = ""
    modelo = ""

    # --------------------------------------------------------
    # C1200 / C1250
    # --------------------------------------------------------

    if "C1250" in nome:
        familia = "C1200"
        modelo = "C1250"

    elif "C1200" in nome:
        familia = "C1200"
        modelo = "C1200"

    # --------------------------------------------------------
    # NDC
    # --------------------------------------------------------

    elif "NDC_ME03" in nome:
        familia = "NDC"
        modelo = "NDC_ME03"

    elif "A-NDC" in nome:
        familia = "NDC"
        modelo = "A-NDC"

    elif "NDC" in nome:
        familia = "NDC"
        modelo = "NDC"

    # --------------------------------------------------------
    # Caso não seja identificado
    # --------------------------------------------------------

    else:
        familia = ""
        modelo = ""

    return familia, modelo


# ============================================================
# HASH DO ARQUIVO
# ============================================================

def calcular_hash(caminho):
    sha256 = hashlib.sha256()

    with open(caminho, "rb") as arquivo:
        while True:
            bloco = arquivo.read(1024 * 1024)

            if not bloco:
                break

            sha256.update(bloco)

    return sha256.hexdigest()


# ============================================================
# INÍCIO
# ============================================================

print()
print("=" * 70)
print("                 RAG - ATUALIZAR BANCO")
print("=" * 70)
print()

if not PASTA_DOCUMENTOS.exists():

    print("ERRO: pasta documentos não encontrada.")
    print(PASTA_DOCUMENTOS)
    exit()


PASTA_BANCO.mkdir(parents=True, exist_ok=True)


# ============================================================
# MODELO DE EMBEDDING
# ============================================================

print("Carregando modelo de embeddings...")

modelo = SentenceTransformer("all-MiniLM-L6-v2")

print("Modelo carregado.")
print()


# ============================================================
# CHROMADB
# ============================================================

cliente = chromadb.PersistentClient(
    path=str(PASTA_BANCO)
)

colecao = cliente.get_or_create_collection(
    name=NOME_COLECAO
)

print(f"Registros atuais no banco: {colecao.count()}")
print()


# ============================================================
# SPLITTER
# ============================================================

splitter = RecursiveCharacterTextSplitter(
    chunk_size=TAMANHO_CHUNK,
    chunk_overlap=OVERLAP_CHUNK
)


# ============================================================
# LISTA DE PDFs
# ============================================================

arquivos_pdf = sorted(
    PASTA_DOCUMENTOS.glob("*.pdf")
)

print(f"PDFs encontrados: {len(arquivos_pdf)}")
print()


if not arquivos_pdf:

    print("Nenhum PDF encontrado.")
    exit()


# ============================================================
# CONTADORES
# ============================================================

quantidade_novos = 0
quantidade_atualizados = 0
quantidade_ignorados = 0


# ============================================================
# PROCESSAMENTO
# ============================================================

for arquivo in arquivos_pdf:

    print("-" * 70)
    print(f"Arquivo: {arquivo.name}")

    hash_atual = calcular_hash(arquivo)

    familia, modelo_equipamento = identificar_equipamento(
        arquivo.name
    )

    print(
        f"Família: {familia if familia else 'Não identificada'}"
    )

    print(
        f"Modelo: {modelo_equipamento if modelo_equipamento else 'Não identificado'}"
    )

    # --------------------------------------------------------
    # Verificar se já existe este arquivo no banco
    # --------------------------------------------------------

    resultado_existente = colecao.get(
        where={
            "arquivo": arquivo.name
        },
        include=["metadatas"]
    )

    metadatas_existentes = resultado_existente.get(
        "metadatas",
        []
    )

    hashes_existentes = set()

    for metadata in metadatas_existentes:

        if metadata and metadata.get("hash"):
            hashes_existentes.add(
                metadata.get("hash")
            )

    # --------------------------------------------------------
    # Arquivo já indexado e sem alteração
    # --------------------------------------------------------

    if hash_atual in hashes_existentes:

        print("Status: sem alteração.")
        print("Ação: ignorado.")

        quantidade_ignorados += 1

        continue

    # --------------------------------------------------------
    # Arquivo alterado
    # --------------------------------------------------------

    if metadatas_existentes:

        print("Status: arquivo alterado.")
        print("Ação: removendo versão anterior...")

        ids_antigos = resultado_existente.get(
            "ids",
            []
        )

        if ids_antigos:

            colecao.delete(
                ids=ids_antigos
            )

        quantidade_atualizados += 1

    else:

        print("Status: arquivo novo.")
        print("Ação: indexando...")

        quantidade_novos += 1

    # --------------------------------------------------------
    # Ler PDF
    # --------------------------------------------------------

    loader = PyPDFLoader(
        str(arquivo)
    )

    paginas = loader.load()

    print(
        f"Páginas encontradas: {len(paginas)}"
    )

    # --------------------------------------------------------
    # Criar chunks
    # --------------------------------------------------------

    documentos = splitter.split_documents(
        paginas
    )

    print(
        f"Chunks criados: {len(documentos)}"
    )

    if not documentos:
        print("AVISO: nenhum texto encontrado.")
        continue

    # --------------------------------------------------------
    # Preparar textos
    # --------------------------------------------------------

    textos = []

    metadatas = []

    ids = []

    for i, documento in enumerate(documentos):

        texto = documento.page_content.strip()

        if not texto:
            continue

        textos.append(texto)

        pagina = documento.metadata.get(
            "page",
            0
        )

        # PDF usa página iniciando em 0.
        # Para exibição usamos página iniciando em 1.
        pagina_exibicao = int(pagina) + 1

        metadatas.append(
            {
                "arquivo": arquivo.name,
                "pagina": pagina_exibicao,
                "hash": hash_atual,
                "familia": familia,
                "modelo": modelo_equipamento,
            }
        )

        ids.append(
            f"{arquivo.stem}_{hash_atual[:12]}_{i}"
        )

    if not textos:
        print("AVISO: nenhum texto válido encontrado.")
        continue

    # --------------------------------------------------------
    # Gerar embeddings
    # --------------------------------------------------------

    print("Gerando embeddings...")

    embeddings = modelo.encode(
        textos,
        show_progress_bar=True
    ).tolist()

    # --------------------------------------------------------
    # Inserir no Chroma
    # --------------------------------------------------------

    colecao.add(
        ids=ids,
        documents=textos,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(
        f"Indexados: {len(textos)} chunks."
    )


# ============================================================
# RESUMO
# ============================================================

print()
print("=" * 70)
print("                 PROCESSAMENTO FINALIZADO")
print("=" * 70)
print()

print(
    f"Arquivos novos:      {quantidade_novos}"
)

print(
    f"Arquivos atualizados: {quantidade_atualizados}"
)

print(
    f"Arquivos ignorados:  {quantidade_ignorados}"
)

print()
print(
    f"Total de registros no banco: {colecao.count()}"
)

print()