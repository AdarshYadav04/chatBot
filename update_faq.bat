@echo off
REM Script to update FAQ and rebuild vector database
echo Updating FAQ and rebuilding vector database...
echo.

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please create a .env file with your GEMINI_API_KEY
    pause
    exit /b 1
)

REM Check if faq.txt exists
if not exist app\docs\faq.txt (
    echo ERROR: app\docs\faq.txt not found!
    echo Please create the FAQ file first.
    pause
    exit /b 1
)

echo Step 1: Running ingestion to update vector database...
echo.
uv run python app/ingest.py

if errorlevel 1 (
    echo ERROR: Ingestion failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo FAQ updated successfully!
echo Vector database has been rebuilt.
echo ========================================
echo.
echo You can now restart your server to use the updated FAQ.
pause

