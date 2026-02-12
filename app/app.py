"""FastAPI application for FAQ chatbot with RAG."""
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain

from app.config import settings, validate_settings
from app.retriever import get_retriever, RetrievalError

# Configure logging first
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Validate settings
try:
    validate_settings()
except ValueError as e:
    logger.warning(f"Settings validation: {e}")

# Global chain instance
retrieval_chain: Any = None
_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    logger.info("Starting application...")
    try:
        initialize_rag_chain()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


def initialize_rag_chain() -> None:
    """Initialize the RAG chain with retriever and LLM."""
    global retrieval_chain
    
    try:
        logger.info("Initializing RAG chain...")
        
        # Get retriever from retriever module
        retriever = get_retriever()
        logger.info("Retriever initialized")
        
        # Initialize LLM with production settings
        llm_kwargs = {
            "model": settings.LLM_MODEL,
            "google_api_key": settings.GEMINI_API_KEY,
            "temperature": settings.LLM_TEMPERATURE,
        }
        if settings.LLM_MAX_TOKENS:
            llm_kwargs["max_output_tokens"] = settings.LLM_MAX_TOKENS
        
        llm = ChatGoogleGenerativeAI(**llm_kwargs)
        logger.info(f"LLM initialized: {settings.LLM_MODEL} (temperature={settings.LLM_TEMPERATURE})")
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_template("""
            You are an expert assistant. Answer the user's question **strictly using the information provided in the context**.

            Rules:
            1. If the context contains the answer, give a **clear, concise, and accurate answer**.
            2. If the answer is **not fully present** in the context:
            - Provide a **short helpful response** based only on general knowledge.
            - Do NOT hallucinate any facts that are not supported by the context.
            3. If the context is empty or irrelevant, respond with a polite message indicating that you don't have enough information to answer.

            <context>
            {context}
            </context>

            Question: {input}
            """)
        
        # Create chains
        document_chain = create_stuff_documents_chain(llm, prompt)
        retrieval_chain = create_retrieval_chain(retriever, document_chain)
        
        logger.info("RAG chain initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG chain: {e}", exc_info=True)
        raise


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FAQ Chatbot API with RAG (Retrieval Augmented Generation)",
    lifespan=lifespan,
)

# Add CORS middleware with production-ready configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

# Add request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests for tracing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{process_time:.4f}"
    
    return response


# ---------- Request/Response Models ----------
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The question to ask the chatbot"
    )
    
    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and clean the question."""
        question = v.strip()
        if not question:
            raise ValueError("Question cannot be empty")
        return question


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str = Field(..., description="The answer from the chatbot")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    message: str
    version: str
    environment: str


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""
    uptime_seconds: float
    status: str
    version: str


# ---------- Exception Handlers ----------
@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Validation error", "detail": str(exc)}
    )


@app.exception_handler(RetrievalError)
async def retrieval_error_handler(request: Request, exc: RetrievalError):
    """Handle retrieval-specific errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Retrieval error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Retrieval service unavailable",
            "detail": "The retrieval service is temporarily unavailable. Please try again later.",
            "request_id": request_id
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with request ID."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    detail = "An unexpected error occurred" if settings.ENVIRONMENT == "production" else str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": detail,
            "request_id": request_id
        }
    )


# ---------- Routes ----------
@app.get("/", response_model=Dict[str, str])
def root():
    """Root endpoint."""
    return {
        "status": "ok",
        "message": f"{settings.APP_NAME} is running",
        "version": settings.APP_VERSION
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        HealthResponse with service status
    """
    try:
        # Verify retriever is available
        if retrieval_chain is None:
            return HealthResponse(
                status="unhealthy",
                message="RAG chain not initialized",
                version=settings.APP_VERSION,
                environment=settings.ENVIRONMENT
            )
        
        # Quick test of retriever
        try:
            retriever = get_retriever()
            # This is a lightweight check - we don't actually retrieve
        except Exception as e:
            logger.warning(f"Health check: retriever check failed: {e}")
            return HealthResponse(
                status="degraded",
                message="Retriever check failed",
                version=settings.APP_VERSION,
                environment=settings.ENVIRONMENT
            )
        
        return HealthResponse(
            status="healthy",
            message="Service is operational",
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            message="Service health check failed",
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT
        )


@app.get("/metrics", response_model=MetricsResponse)
def metrics():
    """
    Metrics endpoint for monitoring.
    
    Returns:
        MetricsResponse with service metrics
    """
    uptime = time.time() - _start_time
    return MetricsResponse(
        uptime_seconds=uptime,
        status="healthy" if retrieval_chain is not None else "unhealthy",
        version=settings.APP_VERSION
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, http_request: Request):
    """
    Chat endpoint for asking questions.
    
    Args:
        request: Chat request containing the question
        http_request: FastAPI request object for accessing request ID
        
    Returns:
        ChatResponse with the answer
        
    Raises:
        HTTPException: If the RAG chain is not initialized or an error occurs
    """
    request_id = getattr(http_request.state, "request_id", "unknown")
    start_time = time.time()
    
    if retrieval_chain is None:
        logger.error(f"[{request_id}] RAG chain not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG chain not initialized. Please check server logs."
        )
    
    try:
        logger.info(f"[{request_id}] Processing question: {request.question[:100]}...")
        
        # Invoke the retrieval chain with timeout handling
        try:
            result = retrieval_chain.invoke({"input": request.question})
        except RetrievalError as e:
            logger.error(f"[{request_id}] Retrieval error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to retrieve relevant information. Please try again later."
            )
        except Exception as e:
            logger.error(f"[{request_id}] Chain invocation error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing your question. Please try again."
            )
        
        # Extract answer from result
        answer = (
            result.get("answer") or 
            result.get("output_text") or 
            result.get("output") or
            str(result)
        )
        
        if not answer or not answer.strip():
            logger.warning(f"[{request_id}] Empty answer received from chain")
            answer = "I apologize, but I couldn't generate a response. Please try rephrasing your question."
        
        elapsed_time = time.time() - start_time
        logger.info(f"[{request_id}] Question processed successfully in {elapsed_time:.2f}s")
        return ChatResponse(answer=answer)
        
    except HTTPException:
        raise
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(
            f"[{request_id}] Error processing question after {elapsed_time:.2f}s: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your question. Please try again."
        )
