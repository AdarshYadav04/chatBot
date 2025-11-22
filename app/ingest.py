import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain
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


embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001", google_api_key=GEMINI_API_KEY)
vectorstore = FAISS.from_documents(docs, embeddings)  
vectorstore.save_local(VECTORDB_PATH)   
print("Ingestion complete. Vector store saved at:", VECTORDB_PATH)  




llm=ChatGoogleGenerativeAI(model="gemini-2.5-flash",google_api_key=GEMINI_API_KEY)

prompt=ChatPromptTemplate.from_template("""
Answer the following question based only on the provided context. 
Think step by step before providing a detailed answer. 
<context>
{context}
</context>
Question: {input}""")

document_chain=create_stuff_documents_chain(llm,prompt)

retriever=vectorstore.as_retriever()

retrieval_chain=create_retrieval_chain(retriever,document_chain)


response=retrieval_chain.invoke({"input":"How do I shorten a URL?"})
print(response['answer'])









