#!/bin/bash
# Script to update FAQ and rebuild vector database

echo "Updating FAQ and rebuilding vector database..."
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please create a .env file with your GEMINI_API_KEY"
    exit 1
fi

# Check if faq.txt exists
if [ ! -f "app/docs/faq.txt" ]; then
    echo "ERROR: app/docs/faq.txt not found!"
    echo "Please create the FAQ file first."
    exit 1
fi

echo "Step 1: Running ingestion to update vector database..."
echo
uv run python app/ingest.py

if [ $? -ne 0 ]; then
    echo "ERROR: Ingestion failed!"
    exit 1
fi

echo
echo "========================================"
echo "FAQ updated successfully!"
echo "Vector database has been rebuilt."
echo "========================================"
echo
echo "You can now restart your server to use the updated FAQ."

