import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VECTORDB_PATH = os.getenv("VECTORDB_PATH", "./vectordb")



loader=TextLoader("app/docs/faq.txt")
load_docs=loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=250,
    chunk_overlap=10,
)
docs=text_splitter.split_documents(load_docs)

# Create and save vector store

embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001", google_api_key=GEMINI_API_KEY)
vectorstore = FAISS.from_documents(docs, embeddings)  
vectorstore.save_local(VECTORDB_PATH)   
print("Ingestion complete. Vector store saved at:", VECTORDB_PATH)  










