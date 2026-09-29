from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

arquivo = r"E:\RAG\documentos\0185-1017-E_1V2_DS_Drives_C1200.pdf"

# Carrega o PDF
loader = PyPDFLoader(arquivo)
documentos = loader.load()

# Divide o texto em pedaços
divisor = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150
)

trechos = divisor.split_documents(documentos)

print(f"Quantidade de páginas: {len(documentos)}")
print(f"Quantidade de trechos: {len(trechos)}")

for i, trecho in enumerate(trechos[:5]):
    print("\n" + "=" * 60)
    print(f"TRECHO {i + 1}")
    print("=" * 60)
    print(trecho.page_content)