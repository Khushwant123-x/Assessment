from langchain_community.document_loaders import PyPDFLoader
loader = PyPDFLoader("Khushwant_ML_Engineer_Resume.pdf")
from langchain_text_splitters import RecursiveCharacterTextSplitter


text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = loader.load()
chunks = text_splitter.split_documents(docs)
print(len(chunks))
print(chunks[0].page_content[:1000])  