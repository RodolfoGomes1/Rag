from sentence_transformers import SentenceTransformer

print("Carregando modelo...")

modelo = SentenceTransformer("all-MiniLM-L6-v2")

texto = "O Servo Drive C1200 suporta comunicação EtherCAT."

vetor = modelo.encode(texto)

print("Embedding gerado!")
print(f"Quantidade de números: {len(vetor)}")
print("Primeiros valores:")
print(vetor[:10])