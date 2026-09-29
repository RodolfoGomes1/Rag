from flask import Flask, render_template, request, jsonify
from google import genai
from pathlib import Path
import sys
import os

# Adiciona a pasta src ao path para conseguir importar o busca.py
sys.path.append(str(Path(__file__).parent / "src"))
from busca import buscar

app = Flask(__name__)

# Configuração do Gemini (pode usar "gemini-3.5-flash-lite" ou "gemini-3.6-flash")
MODELO_GEMINI = "gemini-3.5-flash-lite"
cliente_gemini = genai.Client()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/perguntar", methods=["POST"])
def perguntar():
    dados = request.get_json()
    pergunta_usuario = dados.get("pergunta", "").strip()

    if not pergunta_usuario:
        return jsonify({"resposta": "Por favor, digite uma pergunta válida."})

    try:
        # 1. TRADUÇÃO DA PERGUNTA PARA O INGLÊS (Query Translation)
        prompt_traducao = f"""
Translate the following technical question from Portuguese to English. 
Keep industrial automation terms accurate (e.g., supply voltage, driver, motor phases, wiring).
Return ONLY the translated question in English, without extra text or explanations.

Question: {pergunta_usuario}
"""
        resposta_traducao = cliente_gemini.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt_traducao
        )
        pergunta_em_ingles = resposta_traducao.text.strip()

        # 2. BUSCA NO BANCO VETORIAL USANDO A PERGUNTA TRADUZIDA
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            resultados = buscar(pergunta_em_ingles)
        finally:
            sys.stdout.close()
            sys.stdout = sys.__stdout__

        if not resultados:
            return jsonify({"resposta": "Não encontrei essa informação no manual."})

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

        # 4. GERAÇÃO DA RESPOSTA FINAL EM PORTUGUÊS (com o prompt otimizado para síntese)
        prompt_final = f"""
Responda à pergunta original do usuário (em português) utilizando SOMENTE as informações presentes nos trechos do manual fornecidos abaixo (que estão em inglês).

Se a informação não estiver presente nos trechos, diga claramente:
"Não encontrei essa informação no manual."

Não invente informações. Responda em português, e sempre que possível, informe a página e o arquivo do manual onde encontrou a informação.


PERGUNTA ORIGINAL DO USUÁRIO:
{pergunta_usuario}

TRECHOS DO MANUAL:
{contexto}
"""

        resposta_gemini = cliente_gemini.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt_final
        )

        texto_resposta = resposta_gemini.text

        return jsonify({
            "resposta": texto_resposta,
            "fontes": fontes_utilizadas
        })

    except Exception as e:
        sys.stdout = sys.__stdout__
        return jsonify({"resposta": f"Ocorreu um erro ao processar a requisição: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)