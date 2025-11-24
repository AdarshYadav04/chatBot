import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel


from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VECTORDB_PATH = os.getenv("VECTORDB_PATH", "./vectordb")

app = FastAPI()

# ---------- Models ----------
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

# ---------- RAG Setup (runs once when server starts) ----------
embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    google_api_key=GEMINI_API_KEY,
)

# IMPORTANT: allow_dangerous_deserialization is required for FAISS in new langchain versions
vectorstore = FAISS.load_local(
    VECTORDB_PATH,
    embeddings,
    allow_dangerous_deserialization=True,
)

retriever = vectorstore.as_retriever()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY
)

prompt = ChatPromptTemplate.from_template("""
You are an expert assistant. Answer the user's question **strictly using the information provided in the context**.

Rules:
1. If the context contains the answer, give a **clear, concise, and accurate answer**.
2. If the answer is **not fully present** in the context:
   - Provide a **short helpful response** based only on general knowledge.
   - Do NOT hallucinate any facts that are not supported by the context.
3. Always mention in one sentence if the information was missing or incomplete.

<context>
{context}
</context>

Question: {input}

""")


document_chain = create_stuff_documents_chain(llm, prompt)
retrieval_chain = create_retrieval_chain(retriever, document_chain)


# ---------- Routes ----------
@app.get("/")
def root():
    return {"status": "ok", "message": "FAQ chatbot API running"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = retrieval_chain.invoke({"input": request.question})
    # result is usually {'answer': '...', 'context': [...]}
    answer = result.get("answer") or result.get("output_text") or str(result)
    return ChatResponse(answer=answer)
