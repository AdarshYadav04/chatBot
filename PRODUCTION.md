# Production Deployment Guide

This guide covers deploying the FAQ Chatbot API to production environments.

## Pre-Deployment Checklist

- [ ] All environment variables are configured
- [ ] Vector database has been created and tested
- [ ] API keys are secured (not in code)
- [ ] CORS origins are properly configured
- [ ] Logging is configured
- [ ] Health checks are working
- [ ] Error handling is tested

## Environment Variables

Create a `.env` file with production settings:

```env
# Required
GEMINI_API_KEY=your_production_api_key

# Vector Database
VECTORDB_PATH=./vectordb

# Application
ENVIRONMENT=production
DEBUG=False
APP_NAME=FAQ Chatbot API
APP_VERSION=1.0.0

# CORS - IMPORTANT: Set specific origins in production
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# API Configuration
API_TIMEOUT=60.0
RATE_LIMIT_PER_MINUTE=60
MAX_REQUEST_SIZE=1048576

# LLM Configuration
LLM_MODEL=gemini-2.5-flash
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=1000
LLM_TIMEOUT=30.0

# Retrieval Configuration
RETRIEVER_K=4
RETRIEVER_SEARCH_TYPE=similarity
RETRIEVAL_TIMEOUT=30.0
RETRIEVAL_MAX_RETRIES=3
```

## Deployment Options

### Option 1: Gunicorn with Uvicorn Workers (Recommended)

This is the recommended approach for production.

```bash
# Install gunicorn (already in dependencies)
uv sync

# Run with gunicorn
gunicorn app.app:app \
    --config gunicorn_config.py \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

Or use the config file:

```bash
gunicorn app.app:app --config gunicorn_config.py
```

### Option 2: Uvicorn (Development/Testing)

For development or small deployments:

```bash
uvicorn app.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
```

### Option 3: Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run with gunicorn
CMD ["uv", "run", "gunicorn", "app.app:app", "--config", "gunicorn_config.py"]
```

Build and run:

```bash
docker build -t faq-chatbot .
docker run -p 8000:8000 --env-file .env faq-chatbot
```

## Security Best Practices

### 1. API Key Security
- Never commit API keys to version control
- Use environment variables or secret management services
- Rotate keys regularly
- Use different keys for development and production

### 2. CORS Configuration
- **Never use `*` in production**
- Specify exact origins:
  ```env
  CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
  ```

### 3. Rate Limiting
Consider adding rate limiting middleware:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("10/minute")
def chat(request: ChatRequest):
    ...
```

### 4. Input Validation
- Already implemented with Pydantic models
- Max request size is configurable
- Question length is limited (1-1000 characters)

### 5. Error Handling
- Don't expose internal errors in production
- Use request IDs for tracing
- Log errors securely

## Monitoring

### Health Checks

The application provides health check endpoints:

```bash
# Basic health check
curl http://localhost:8000/health

# Metrics endpoint
curl http://localhost:8000/metrics
```

### Logging

Configure logging for production:

```python
# In app/app.py, you can customize logging
import logging
from app.utils import setup_logging

setup_logging(
    level="INFO",
    log_file="/var/log/chatbot/app.log"
)
```

### Metrics to Monitor

- Response times (check `X-Response-Time` header)
- Error rates
- Request IDs for tracing
- Health check status
- Vector database size
- API key usage/quota

## Performance Tuning

### Worker Configuration

For Gunicorn, adjust workers based on CPU:

```python
# In gunicorn_config.py
workers = (CPU_COUNT * 2) + 1
```

### Vector Database

- Keep vector database on fast storage (SSD)
- Consider caching frequently accessed embeddings
- Monitor vector database size

### LLM Configuration

- Adjust `LLM_MAX_TOKENS` based on expected response length
- Use appropriate `LLM_TEMPERATURE` for consistency
- Monitor API quotas and rate limits

## Reverse Proxy Setup

### Nginx Configuration

```nginx
upstream chatbot {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://chatbot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### SSL/TLS

Use Let's Encrypt for free SSL certificates:

```bash
certbot --nginx -d yourdomain.com
```

## Scaling

### Horizontal Scaling

- Use a load balancer (nginx, AWS ALB, etc.)
- Run multiple Gunicorn instances
- Share vector database across instances (network storage)

### Vertical Scaling

- Increase worker count
- Use more powerful CPUs for embeddings
- Increase memory for larger vector databases

## Backup and Recovery

### Vector Database Backup

```bash
# Backup
tar -czf vectordb_backup_$(date +%Y%m%d).tar.gz ./vectordb/

# Restore
tar -xzf vectordb_backup_YYYYMMDD.tar.gz
```

### Configuration Backup

- Store `.env` files securely
- Use version control for configuration templates
- Document all environment-specific settings

## Troubleshooting

### Common Issues

1. **Vector database not found**
   - Run ingestion: `uv run python app/ingest.py`
   - Check `VECTORDB_PATH` environment variable

2. **API key errors**
   - Verify `GEMINI_API_KEY` is set correctly
   - Check API key quotas/limits

3. **Slow responses**
   - Check worker count
   - Monitor vector database access
   - Check LLM API response times

4. **Memory issues**
   - Reduce worker count
   - Optimize vector database size
   - Monitor memory usage

## Production Checklist

Before going live:

- [ ] All tests passing
- [ ] Health checks working
- [ ] Error handling tested
- [ ] Logging configured
- [ ] Monitoring set up
- [ ] CORS properly configured
- [ ] SSL/TLS enabled
- [ ] Rate limiting configured
- [ ] Backup strategy in place
- [ ] Documentation updated
- [ ] Team trained on operations

