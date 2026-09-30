import re
import unicodedata
from pathlib import Path

import torch
import gc

torch.set_grad_enabled(False)

# import chromadb
# from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_PROJETO = Path(__file__).resolve().parent.parent
PASTA_BANCO = PASTA_PROJETO / "banco"

COLECAO = "documentos"

MODELO_EMBEDDING = "all-MiniLM-L6-v2"

TOP_SEMANTICO = 30
TOP_FINAL = 10


# ============================================================
# INSTÂNCIAS GLOBAIS LAZY (Otimizado para poupar RAM no Render)
# ============================================================

_cliente_chroma = None
_modelo_embedding = None

def obter_cliente_chroma():
    global _cliente_chroma
    if _cliente_chroma is None:
        import chromadb
        _cliente_chroma = chromadb.PersistentClient(path=str(PASTA_BANCO))
    return _cliente_chroma

def obter_modelo_embedding():
    global _modelo_embedding
    if _modelo_embedding is None:
        import torch
        # Força o uso de uma única thread para poupar RAM
        torch.set_num_threads(1)
        from sentence_transformers import SentenceTransformer
        _modelo_embedding = SentenceTransformer(MODELO_EMBEDDING, device="cpu")
    return _modelo_embedding


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar(texto):

    texto = str(texto).lower()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9.+-]+", " ", texto)

    return texto.strip()


# ============================================================
# EXTRAÇÃO DE TERMOS
# ============================================================

def extrair_termos(pergunta):

    texto = normalizar(pergunta)

    termos = []

    palavras = texto.split()

    stopwords = {
        "a", "o", "as", "os",
        "de", "da", "do", "das", "dos",
        "qual", "quais",
        "que",
        "como",
        "onde",
        "para",
        "por",
        "um", "uma",
        "e",
        "no", "na",
        "nos", "nas",
        "ao", "aos",
        "se",
        "pode", "podem",
        "ser",
        "ligado", "ligados",
        "ligar"
    }

    for palavra in palavras:

        if palavra in stopwords:
            continue

        if len(palavra) < 2:
            continue

        termos.append(palavra)

    return list(dict.fromkeys(termos))


# ============================================================
# IDENTIFICAÇÃO DE CONTEXTO
# ============================================================

def identificar_contexto(pergunta):

    texto = normalizar(pergunta)

    familia = None
    modelo = None

    # --------------------------------------------------------
    # C1200 / C1250
    # --------------------------------------------------------

    if "c1250" in texto:

        familia = "C1200"
        modelo = "C1250"

    elif "c1200" in texto:

        familia = "C1200"
        modelo = "C1200"

    # --------------------------------------------------------
    # NDC ME03
    # --------------------------------------------------------

    elif "ndc me03" in texto or "ndc_me03" in texto:

        familia = "NDC"
        modelo = "NDC_ME03"

    # --------------------------------------------------------
    # A-NDC
    # --------------------------------------------------------

    elif "a ndc" in texto or "a-ndc" in texto:

        familia = "NDC"
        modelo = "A-NDC"

    # --------------------------------------------------------
    # NDC genérico
    # --------------------------------------------------------

    elif "ndc" in texto:

        familia = "NDC"
        modelo = None

    return familia, modelo


# ============================================================
# IDENTIFICAÇÃO DE INTENÇÃO
# ============================================================

PALAVRAS_INTENCAO = {

    "alimentacao": [

        ("tensao de alimentacao", 20),
        ("tensao", 8),
        ("alimentacao", 10),
        ("alimentacao do drive", 20),

        ("motor supply", 20),
        ("supply voltage", 20),
        ("supply", 5),
        ("voltage", 5),
        ("power supply", 15),

        ("24vdc", 5),
        ("72vdc", 5),
        ("85vdc", 5),
        ("90vdc", 5),
    ],

    "motores": [

        ("modelos de motores", 25),
        ("modelo de motor", 20),
        ("motores podem ser ligados", 25),
        ("motor compativel", 20),
        ("motores compativeis", 25),

        ("controllable motors", 25),
        ("compatible motors", 25),
        ("selected motors", 20),

        ("linmot p0x", 20),
        ("linmot pr0x", 20),

        ("motor", 6),
        ("motors", 6),
    ],

    "alarme_led": [

        ("diagnostico de alarme", 25),
        ("diagnostico", 10),
        ("alarme", 15),
        ("led", 15),
        ("leds", 15),

        ("status by led", 30),
        ("drive status by led", 30),
        ("led status", 20),

        ("luz vermelha", 10),
        ("luz verde", 10),
        ("luz amarela", 10),
    ],

    "comunicacao": [

        ("comunicacao", 15),
        ("comunicacao ethernet", 20),
        ("ethercat", 20),
        ("ethernet", 15),
        ("canopen", 20),
        ("rs232", 15),
        ("rs485", 15),
        ("modbus", 15),
        ("fieldbus", 15),
        ("protocolo", 10),
    ],

    "conexao": [

        ("como conectar", 20),
        ("conectar", 10),
        ("ligacao", 15),
        ("conexao", 15),
        ("pinagem", 20),
        ("pinos", 15),
        ("connector", 10),
        ("connection", 10),
        ("wiring", 15),
    ],
}


def identificar_intencao(pergunta):

    texto = normalizar(pergunta)

    melhor_intencao = "geral"
    melhor_score = 0

    for intencao, regras in PALAVRAS_INTENCAO.items():

        score = 0

        for termo, peso in regras:

            if termo in texto:
                score += peso

        if score > melhor_score:

            melhor_score = score
            melhor_intencao = intencao

    return melhor_intencao


# ============================================================
# SCORE DE INTENÇÃO
# ============================================================

def calcular_score_intencao(texto, intencao):

    texto_normalizado = normalizar(texto)

    regras = PALAVRAS_INTENCAO.get(intencao, [])

    score = 0

    for termo, peso in regras:

        if termo in texto_normalizado:

            score += peso

    return score


# ============================================================
# SCORE LEXICAL
# ============================================================

def calcular_score_lexical(texto, termos):
    texto_normalizado = normalizar(texto)

    palavras_texto = set(texto_normalizado.split())

    score = 0

    for termo in termos:
        termo_normalizado = normalizar(termo)

        if not termo_normalizado:
            continue

        # Termo com várias palavras
        if " " in termo_normalizado:
            if termo_normalizado in texto_normalizado:
                score += 6

                if len(termo_normalizado) >= 10:
                    score += 2

        # Termo com uma palavra
        else:
            if termo_normalizado in palavras_texto:
                score += 4

                if len(termo_normalizado) >= 6:
                    score += 2

    return score

# ============================================================
# SCORE DE CONTEXTO
# ============================================================

def calcular_score_contexto(metadata, familia, modelo):

    score = 0

    familia_doc = metadata.get("familia", "")
    modelo_doc = metadata.get("modelo", "")

    # --------------------------------------------------------
    # FAMÍLIA
    # --------------------------------------------------------

    if familia:

        if familia_doc == familia:

            score += 8

        elif familia_doc:

            # família diferente
            score -= 20

        else:

            # documento sem família
            score -= 10

    # --------------------------------------------------------
    # MODELO
    # --------------------------------------------------------

    if modelo:

        # MODELO EXATO
        if modelo_doc == modelo:

            score += 40

        # OUTRO MODELO DA MESMA FAMÍLIA
        elif familia_doc == familia and modelo_doc:

            score -= 20

        # DOCUMENTO DA MESMA FAMÍLIA,
        # MAS SEM MODELO IDENTIFICADO
        elif familia_doc == familia and not modelo_doc:

            score -= 10

        # MODELO NÃO IDENTIFICADO
        elif not modelo_doc:

            score -= 10

        # MODELO COMPLETAMENTE DIFERENTE
        else:

            score -= 25

    return score


# ============================================================
# PENALIZAÇÃO DE FAMÍLIA
# ============================================================

def calcular_penalidade_familia(metadata, familia):

    if not familia:
        return 0

    familia_doc = metadata.get("familia", "")

    # Documento sem família identificada
    if not familia_doc:
        return -20

    # Mesma família
    if familia_doc == familia:
        return 0

    # Família diferente
    return -35


# ============================================================
# SCORE SEMÂNTICO
# ============================================================

def calcular_score_semantico(distancia):

    """
    Converte a distância L2 retornada pelo Chroma
    em uma pontuação semântica de 0 a 100.
    """

    if distancia is None:
        return 0

    try:
        distancia = float(distancia)

    except (TypeError, ValueError):
        return 0

    if distancia < 0:
        distancia = 0

    score = 100.0 / (1.0 + distancia)

    return score


# ============================================================
# SCORE DE RESPOSTA DIRETA
# ============================================================

PADROES_RESPOSTA = {

    "alimentacao": [

        (r"\b\d+\s*vdc\b", 20),
        (r"\b\d+\s*vac\b", 20),
        (r"\b\d+\s*a\b", 10),

        (r"\b\d+\s*\.\.\.\s*\d+\s*vdc\b", 30),
        (r"\b\d+\s*to\s*\d+\s*vdc\b", 30),

        ("nominal supply voltage", 30),
        ("motor supply", 15),
        ("supply voltage", 15),
        ("logic supply", 10),
        ("absolute max", 15),
    ],

    "motores": [

        ("controllable motors", 40),
        ("compatible motors", 40),
        ("selected motors", 35),
        ("motor compatibility", 35),

        ("linmot p0x", 35),
        ("linmot pr0x", 35),

        ("px motors", 30),
        ("pr motors", 30),

        ("selected motor", 25),
        ("motor types", 25),
    ],

    "alarme_led": [

        ("drive status by led", 40),
        ("status by led", 40),
        ("led status", 30),

        ("led", 10),
        ("error", 10),
        ("warning", 10),
        ("fault", 10),
    ],

    "comunicacao": [

        ("ethercat", 25),
        ("canopen", 25),
        ("rs232", 20),
        ("rs485", 20),
        ("ethernet", 15),
        ("fieldbus", 20),
        ("communication", 20),
    ],

    "conexao": [

        ("connection", 20),
        ("connector", 20),
        ("pin", 15),
        ("wiring", 20),
        ("motor connection", 30),
        ("logic supply / io connection", 30),
    ],
}


def calcular_score_resposta_direta(texto, intencao):

    texto_normalizado = normalizar(texto)

    regras = PADROES_RESPOSTA.get(intencao, [])

    score = 0

    for regra, peso in regras:

        # Regex
        if regra.startswith(r"\b"):

            try:

                if re.search(
                    regra,
                    texto_normalizado
                ):

                    score += peso

            except re.error:

                pass

        # Texto normal
        else:

            if regra in texto_normalizado:

                score += peso

    return score


# ============================================================
# BUSCA
# ============================================================

def buscar(pergunta):

    print()
    print("=" * 70)
    print("PERGUNTA")
    print("=" * 70)
    print(pergunta)

    # --------------------------------------------------------
    # CONTEXTO
    # --------------------------------------------------------

    familia, modelo = identificar_contexto(pergunta)

    print()
    print("CONTEXTO")
    print("-" * 70)
    print(f"Familia : {familia}")
    print(f"Modelo  : {modelo}")

    # --------------------------------------------------------
    # INTENÇÃO
    # --------------------------------------------------------

    intencao = identificar_intencao(pergunta)

    print()
    print("INTENÇÃO")
    print("-" * 70)
    print(intencao)

    # --------------------------------------------------------
    # TERMOS
    # --------------------------------------------------------

    termos = extrair_termos(pergunta)

    # --------------------------------------------------------
    # CHROMA (Usando função global otimizada)
    # --------------------------------------------------------

    cliente = obter_cliente_chroma()

    colecao = cliente.get_collection(
        name=COLECAO
    )

    # --------------------------------------------------------
    # MODELO DE EMBEDDING (Usando cache global otimizado)
    # --------------------------------------------------------

    modelo_embedding = obter_modelo_embedding()

    # --------------------------------------------------------
    # EMBEDDING
    # --------------------------------------------------------

    embedding = modelo_embedding.encode(
        pergunta,
        normalize_embeddings=True
    ).tolist()

    # --------------------------------------------------------
    # BUSCA SEMÂNTICA
    # --------------------------------------------------------

    resultados_semanticos = colecao.query(

        query_embeddings=[embedding],

        n_results=TOP_SEMANTICO,

        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    candidatos = {}

    documentos = resultados_semanticos["documents"][0]
    metadatas = resultados_semanticos["metadatas"][0]
    distances = resultados_semanticos["distances"][0]
    ids = resultados_semanticos["ids"][0]

    for i in range(len(documentos)):

        candidatos[ids[i]] = {

            "texto": documentos[i],

            "metadata": metadatas[i],

            "distancia": distances[i],

            "origem_semantica": True
        }

    # --------------------------------------------------------
    # BUSCA LEXICAL
    # --------------------------------------------------------

    total = colecao.count()

    if total > 0:

        todos = colecao.get(

            include=[
                "documents",
                "metadatas"
            ]
        )

        for i in range(len(todos["documents"])):

            texto = todos["documents"][i]

            metadata = todos["metadatas"][i]

            score_lexical = calcular_score_lexical(
                texto,
                termos
            )

            if score_lexical > 0:

                id_doc = todos["ids"][i]

                if id_doc not in candidatos:

                    candidatos[id_doc] = {

                        "texto": texto,

                        "metadata": metadata,

                        "distancia": None,

                        "origem_semantica": False
                    }

    # --------------------------------------------------------
    # RANKING
    # --------------------------------------------------------

    resultados = []

    for id_doc, item in candidatos.items():

        texto = item["texto"]

        metadata = item["metadata"]

        distancia = item["distancia"]

        # --------------------------------------------
        # SCORES
        # --------------------------------------------

        score_semantico = calcular_score_semantico(
            distancia
        )

        score_lexical = calcular_score_lexical(
            texto,
            termos
        )

        score_contexto = calcular_score_contexto(
            metadata,
            familia,
            modelo
        )

        score_intencao = calcular_score_intencao(
            texto,
            intencao
        )

        penalidade_familia = calcular_penalidade_familia(
            metadata,
            familia
        )

        score_resposta = calcular_score_resposta_direta(
            texto,
            intencao
        )

        # --------------------------------------------
        # SCORE FINAL
        # --------------------------------------------

        score = (

            score_semantico * 0.35

            + score_lexical * 0.40

            + score_resposta * 0.80

            + score_contexto

            + score_intencao

            + penalidade_familia
        )

        resultados.append({

            "id": id_doc,

            "score": score,

            "semantico": score_semantico,

            "lexical": score_lexical,

            "resposta": score_resposta,

            "contexto": score_contexto,

            "intencao": score_intencao,

            "penalidade_familia": penalidade_familia,

            "texto": texto,

            "metadata": metadata,

            "distancia": distancia
        })

    # --------------------------------------------------------
    # ORDENAÇÃO
    # --------------------------------------------------------

    resultados.sort(

        key=lambda x: x["score"],

        reverse=True
    )

    resultados = resultados[:TOP_FINAL]

    gc.collect()

    # --------------------------------------------------------
    # EXIBIÇÃO
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RESULTADOS")
    print("=" * 70)

    for i, resultado in enumerate(
        resultados,
        start=1
    ):

        metadata = resultado["metadata"]

        print()

        print(
            f"[{i}] SCORE: "
            f"{resultado['score']:.2f}"
        )

        print(
            f"    Semântico : "
            f"{resultado['semantico']:.2f}"
        )

        print(
            f"    Lexical   : "
            f"{resultado['lexical']:.2f}"
        )

        print(
            f"    Resposta  : "
            f"{resultado['resposta']:.2f}"
        )

        print(
            f"    Contexto  : "
            f"{resultado['contexto']:.2f}"
        )

        print(
            f"    Intenção  : "
            f"{resultado['intencao']:.2f}"
        )

        print(
            f"    Fam.      : "
            f"{resultado['penalidade_familia']:.2f}"
        )

        if resultado["distancia"] is not None:

            print(
                f"    Distância : "
                f"{resultado['distancia']:.4f}"
            )

        print(
            "    Termos    : "
            + ", ".join(termos)
        )

        print(
            f"    Arquivo   : "
            f"{metadata.get('arquivo', 'N/A')}"
        )

        print(
            f"    Família   : "
            f"{metadata.get('familia', 'N/A')}"
        )

        print(
            f"    Modelo    : "
            f"{metadata.get('modelo', 'N/A')}"
        )

        print(
            f"    Página    : "
            f"{metadata.get('pagina', 'N/A')}"
        )

        print()

        print("    TEXTO:")
        print("    " + "-" * 62)

        texto = resultado["texto"]

        if len(texto) > 2500:

            texto = texto[:2500] + "..."

        print(
            "    " +
            texto.replace(
                "\n",
                "\n    "
            )
        )

    return resultados


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

if __name__ == "__main__":

    print()

    print("=" * 70)
    print("RAG - BUSCA NOS MANUAIS")
    print("=" * 70)

    while True:

        print()

        pergunta = input(
            "Digite sua pergunta (ou ENTER para sair): "
        ).strip()

        if not pergunta:
            break

        try:

            buscar(pergunta)

        except Exception as e:

            print()

            print("=" * 70)
            print("ERRO")
            print("=" * 70)

            print(e)

    print()

    print("RAG encerrado.")
