#!/bin/bash
# Quick start script for Linux/Mac

echo "Starting FAQ Chatbot API..."
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please create a .env file with your GEMINI_API_KEY"
    echo "Example:"
    echo "GEMINI_API_KEY=your_api_key_here"
    echo "VECTORDB_PATH=./vectordb"
    exit 1
fi

# Check if vector database exists
if [ ! -d "app/vectordb" ]; then
    echo "Vector database not found. Running ingestion..."
    echo
    uv run python app/ingest.py
    if [ $? -ne 0 ]; then
        echo "ERROR: Ingestion failed!"
        exit 1
    fi
    echo
fi

# Start the server
echo "Starting FastAPI server..."
echo "API will be available at: http://localhost:8000"
echo "Interactive docs at: http://localhost:8000/docs"
echo
uv run uvicorn app.app:app --reload --host 0.0.0.0 --port 8000

