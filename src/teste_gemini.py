print("1 - Iniciando...")

from google import genai

print("2 - SDK carregado")

client = genai.Client()

print("3 - Cliente criado")

interaction = client.interactions.create(
    model="gemini-3.5-flash-lite",
    input="Responda apenas: TESTE OK"
)

print("4 - Resposta recebida")
print(interaction.output_text)