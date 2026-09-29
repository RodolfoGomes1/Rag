from langchain_community.document_loaders import PyPDFLoader

arquivo = r"E:\RAG\documentos\0185-1017-E_1V2_DS_Drives_C1200.pdf"

loader = PyPDFLoader(arquivo)

documentos = loader.load()

print(f"Quantidade de páginas: {len(documentos)}")

for documento in documentos[:2]:
    print("\n--- PÁGINA ---")
    print(documento.page_content[:1000])