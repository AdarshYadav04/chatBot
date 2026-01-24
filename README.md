# FAQ Chatbot with RAG

A production-ready FAQ chatbot API built with FastAPI, LangChain, and Google Gemini, using Retrieval Augmented Generation (RAG) for accurate question answering.

## Features

- 🚀 Production-ready FastAPI application
- 🔍 RAG-based question answering with FAISS vector store
- 📝 Modular and maintainable code structure
- 🛡️ Comprehensive error handling and logging
- ✅ Request validation and health checks
- ⚙️ Configurable via environment variables

## Prerequisites

- Python 3.13 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- `uv` package manager (recommended) or `pip`

## Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd chatBot
```

### 2. Install Dependencies

**Using `uv` (recommended):**
```bash
uv sync
```

**Using `pip`:**
```bash
pip install -e .
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_api_key_here
VECTORDB_PATH=./vectordb
```

### 4. Ingest Documents (First Time Setup)

Before running the API, you need to create the vector database:

```bash
# Using uv
uv run python app/ingest.py

# Using pip
python app/ingest.py
```

This will:
- Load documents from `app/docs/faq.txt`
- Split them into chunks
- Generate embeddings
- Save the vector store to `./vectordb`

**Note:** The ingestion script automatically finds `app/docs/faq.txt`. You can also specify a custom path using the `DOCS_PATH` environment variable.

### Updating the FAQ

After editing `app/docs/faq.txt`, rebuild the vector database:

**Windows:**
```bash
update_faq.bat
```

**Linux/Mac:**
```bash
chmod +x update_faq.sh
./update_faq.sh
```

**Or manually:**
```bash
uv run python app/ingest.py
```

## Running the Application

### Start the FastAPI Server

**Using `uv`:**
```bash
uv run uvicorn app.app:app --reload --host 0.0.0.0 --port 8000
```

**Using `pip`:**
```bash
uvicorn app.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

### Command Line Options

- `--reload`: Enable auto-reload on code changes (development only)
- `--host 0.0.0.0`: Make the server accessible from all network interfaces
- `--port 8000`: Specify the port (default: 8000)

## API Endpoints

### 1. Root Endpoint
```bash
GET http://localhost:8000/
```

**Response:**
```json
{
  "status": "ok",
  "message": "FAQ Chatbot API is running",
  "version": "1.0.0"
}
```

### 2. Health Check
```bash
GET http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "message": "Service is operational",
  "version": "1.0.0"
}
```

### 3. Chat Endpoint
```bash
POST http://localhost:8000/chat
Content-Type: application/json

{
  "question": "What is your return policy?"
}
```

**Response:**
```json
{
  "answer": "Our return policy allows returns within 30 days of purchase..."
}
```

## Testing the API

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is your return policy?"}'
```

### Using Python requests

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Chat endpoint
response = requests.post(
    "http://localhost:8000/chat",
    json={"question": "What is your return policy?"}
)
print(response.json())
```

### Using the Interactive Docs

Visit http://localhost:8000/docs for Swagger UI where you can test all endpoints interactively.

## Project Structure

```
chatBot/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── app.py               # FastAPI application
│   ├── config.py            # Configuration management
│   ├── retriever.py         # Retrieval logic
│   ├── ingest.py            # Document ingestion script
│   ├── docs/
│   │   └── faq.txt          # FAQ documents
│   └── vectordb/            # Vector database (generated)
├── .env                     # Environment variables (create this)
├── .env.example             # Example environment file
├── pyproject.toml           # Project dependencies
├── uv.lock                  # Dependency lock file
└── README.md                # This file
```

## Configuration

All configuration is done via environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | **Required** |
| `VECTORDB_PATH` | Path to vector database | `./vectordb` |
| `EMBEDDING_MODEL` | Embedding model name | `gemini-embedding-001` |
| `LLM_MODEL` | LLM model name | `gemini-2.5-flash` |
| `RETRIEVER_K` | Number of documents to retrieve | `4` |
| `RETRIEVER_SEARCH_TYPE` | Search type (similarity/mmr) | `similarity` |
| `DEBUG` | Enable debug logging | `False` |

## Development

### Running in Development Mode

```bash
uvicorn app.app:app --reload
```

The `--reload` flag enables auto-reload on code changes.

### Adding New Documents

1. Add your documents to `app/docs/faq.txt` (or create new files)
2. Update `app/ingest.py` to load your documents
3. Run the ingestion script again:
   ```bash
   uv run python app/ingest.py
   ```

### Logging

Logs are configured in `app/app.py`. Set `DEBUG=True` in `.env` for detailed logging.

## Troubleshooting

### Vector Database Not Found

If you see an error about the vector database:
```bash
# Run the ingestion script first
uv run python app/ingest.py
```

### API Key Issues

Make sure your `.env` file contains a valid `GEMINI_API_KEY`:
```bash
# Check your .env file
cat .env
```

### Port Already in Use

If port 8000 is already in use:
```bash
# Use a different port
uvicorn app.app:app --port 8001
```

## Production Deployment

For production deployment, see [PRODUCTION.md](PRODUCTION.md) for detailed instructions.

Quick start with Gunicorn:

```bash
# Using the config file
gunicorn app.app:app --config gunicorn_config.py

# Or with command line options
gunicorn app.app:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
```

**Important Production Settings:**

1. Set `ENVIRONMENT=production` in `.env`
2. Configure `CORS_ORIGINS` with specific domains (never use `*`)
3. Set `DEBUG=False`
4. Use Gunicorn with multiple workers
5. Set up reverse proxy (nginx) with SSL
6. Configure monitoring and logging
7. Set up health check monitoring

## License

Author - Adarsh Yadav
