@echo off
REM Quick start script for Windows
echo Starting FAQ Chatbot API...
echo.

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please create a .env file with your GEMINI_API_KEY
    echo Example:
    echo GEMINI_API_KEY=your_api_key_here
    echo VECTORDB_PATH=./vectordb
    pause
    exit /b 1
)

REM Check if vector database exists
if not exist app\vectordb (
    echo Vector database not found. Running ingestion...
    echo.
    uv run python app/ingest.py
    if errorlevel 1 (
        echo ERROR: Ingestion failed!
        pause
        exit /b 1
    )
    echo.
)

REM Start the server
echo Starting FastAPI server...
echo API will be available at: http://localhost:8000
echo Interactive docs at: http://localhost:8000/docs
echo.
uv run uvicorn app.app:app --reload --host 0.0.0.0 --port 8000

