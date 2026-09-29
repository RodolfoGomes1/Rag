from flask import Flask, render_template, request, jsonify, session
from google import genai
from pathlib import Path
import sys
import os

# Adiciona a pasta src ao path para conseguir importar o busca.py
sys.path.append(str(Path(__file__).parent / "src"))
from busca import buscar

app = Flask(__name__)
app.secret_key = "chave_secreta_rag_industrial" # Necessário para gerenciar a sessão do chat

# Configuração do Gemini (Modelo Lite)
MODELO_GEMINI = "gemini-3.5-flash-lite"
cliente_gemini = genai.Client()

@app.route("/")
def index():
    # Inicializa o histórico da conversa na sessão ao carregar a página
    session["historico"] = []
    return render_template("index.html")

@app.route("/perguntar", methods=["POST"])
def perguntar():
    dados = request.get_json()
    pergunta_usuario = dados.get("pergunta", "").strip()

    if not pergunta_usuario:
        return jsonify({"resposta": "Por favor, digite uma pergunta válida."})

    # Recupera o histórico da sessão atual
    historico = session.get("historico", [])

    try:
        # 1. REESCRITA / TRADUÇÃO DA PERGUNTA COM BASE NO HISTÓRICO (Query Rewriting)
        # Se o usuário disse "E qual o consumo?", isso traduz considerando as mensagens anteriores para incluir o sujeito correto (ex: "NDC current consumption")
        prompt_conversacional = f"""
Given the conversation history and the user's latest question in Portuguese, formulate a precise technical question in English for an industrial vector database search. If the latest question references previous topics (e.g., using pronouns like "it", "this model"), resolve them using the history.
Return ONLY the final translated and contextualized question in English.

Conversation History:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in historico[-4:]])}

Latest User Question (Portuguese): {pergunta_usuario}
"""
        resposta_traducao = cliente_gemini.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt_conversacional
        )
        pergunta_busca_ingles = resposta_traducao.text.strip()

        # 2. BUSCA NO BANCO VETORIAL USANDO A PERGUNTA CONTEXTUALIZADA
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            resultados = buscar(pergunta_busca_ingles)
        finally:
            sys.stdout.close()
            sys.stdout = sys.__stdout__

        if not resultados:
            resposta_texto = "Não encontrei essa informação no manual."
            fontes_utilizadas = []
        else:
            # 3. MONTAGEM DO CONTEXTO COM OS MELHORES TRECHOS
            contexto = ""
            fontes_utilizadas = []

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
                fonte_info = f"{arquivo} (Pág. {pagina})"
                if fonte_info not in fontes_utilizadas:
                    fontes_utilizadas.append(fonte_info)

            # 4. GERAÇÃO DA RESPOSTA FINAL EM PORTUGUÊS (Com histórico e foco em síntese)
            prompt_final = f"""
Responda à pergunta original do usuário (em português) utilizando SOMENTE as informações presentes nos trechos do manual fornecidos abaixo (que estão em inglês).

Se a informação não estiver presente nos trechos, diga claramente:
"Não encontrei essa informação no manual."

Não invente informações. Responda em português, e sempre que possível, informe a página e o arquivo do manual onde encontrou a informação.


Histórico recente:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in historico[-4:]])}

Pergunta Atual do Usuário: {pergunta_usuario}

Trechos do Manual:
{contexto}
"""

            resposta_gemini = cliente_gemini.models.generate_content(
                model=MODELO_GEMINI,
                contents=prompt_final
            )
            resposta_texto = resposta_gemini.text

        # Atualiza o histórico na sessão
        historico.append({"role": "User", "content": pergunta_usuario})
        historico.append({"role": "Assistant", "content": resposta_texto})
        session["historico"] = historico

        return jsonify({
            "resposta": resposta_texto,
            "fontes": fontes_utilizadas
        })

    except Exception as e:
        sys.stdout = sys.__stdout__
        return jsonify({"resposta": f"Ocorreu um erro ao processar a requisição: {str(e)}"}), 500

@app.route("/limpar", methods=["POST"])
def limpar():
    session["historico"] = []
    return jsonify({"status": "limpo"})

if __name__ == "__main__":
    app.run(debug=True, port=5001)