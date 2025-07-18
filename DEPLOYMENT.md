# 🚀 Deployment Guide

This guide covers all deployment options for the Personal MCP Server, from local development to production cloud deployment.

## 📋 Table of Contents

- [Local Development](#-local-development)
- [Docker Deployment](#-docker-deployment)
- [Cloud Deployment](#-cloud-deployment)
- [Environment Variables](#-environment-variables)
- [Monitoring & Health Checks](#-monitoring--health-checks)

---

## 💻 Local Development

### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run in HTTP mode (for web API)
python3 unified_mcp_server.py --http

# Run in MCP mode (for AI assistants like Cline)
python3 mcp_server.py
```

### Development with Auto-Reload
```bash
# HTTP mode with auto-reload
uvicorn unified_mcp_server:app --reload --host 0.0.0.0 --port 8000

# Access the API
open http://localhost:8000/docs
```

---

## 🐳 Docker Deployment

### Single Container
```bash
# Build the image
docker build -t personal-mcp-server .

# Run the container
docker run -p 8000:8000 \
  -v $(pwd)/context_data.json:/app/context_data.json \
  personal-mcp-server
```

### Docker Compose (Recommended)
```bash
# Development mode
docker-compose up --build

# Production mode with nginx
docker-compose --profile production up --build -d

# View logs
docker-compose logs -f mcp-server
```

### Docker Compose Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up --build

# View logs
docker-compose logs -f

# Scale the service
docker-compose up --scale mcp-server=3
```

---

## ☁️ Cloud Deployment

### 1. Heroku Deployment

#### Prerequisites
- Heroku CLI installed
- Git repository

#### Deploy Steps
```bash
# Login to Heroku
heroku login

# Create Heroku app
heroku create your-mcp-server-name

# Set environment variables (optional)
heroku config:set PORT=8000

# Deploy
git push heroku main

# View logs
heroku logs --tail

# Open the app
heroku open
```

#### Heroku Configuration
The `Procfile` is already configured:
```
web: uvicorn unified_mcp_server:app --host 0.0.0.0 --port $PORT
```

### 2. Railway Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### 3. Render Deployment

1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python unified_mcp_server.py --http`
   - **Environment**: Python 3.11

### 4. DigitalOcean App Platform

1. Connect your GitHub repository
2. Configure the app:
   ```yaml
   name: personal-mcp-server
   services:
   - name: web
     source_dir: /
     github:
       repo: your-username/personal-mcp-server
       branch: main
     run_command: python unified_mcp_server.py --http
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
     http_port: 8000
   ```

### 5. Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/personal-mcp-server

# Deploy to Cloud Run
gcloud run deploy personal-mcp-server \
  --image gcr.io/PROJECT_ID/personal-mcp-server \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 6. AWS ECS/Fargate

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker build -t personal-mcp-server .
docker tag personal-mcp-server:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/personal-mcp-server:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/personal-mcp-server:latest

# Deploy using ECS CLI or AWS Console
```

---

## 🔧 Environment Variables

### Required Variables
- `PORT` - Server port (default: 8000)

### Optional Variables
- `PYTHONUNBUFFERED` - Set to 1 for immediate stdout/stderr output
- `PYTHONDONTWRITEBYTECODE` - Set to 1 to prevent .pyc files

### Setting Environment Variables

#### Local Development
```bash
export PORT=8000
export PYTHONUNBUFFERED=1
```

#### Docker
```bash
docker run -e PORT=8000 -e PYTHONUNBUFFERED=1 personal-mcp-server
```

#### Heroku
```bash
heroku config:set PORT=8000
heroku config:set PYTHONUNBUFFERED=1
```

---

## 📊 Monitoring & Health Checks

### Health Check Endpoint
```bash
curl http://localhost:8000/status
```

Response:
```json
{
  "status": "ok",
  "stored_contexts": ["context1", "context2"],
  "total_items": 42,
  "server_uptime": "2:30:15",
  "mcp_tools": 15,
  "mcp_resources": 6
}
```

### Docker Health Check
The Dockerfile includes a health check:
```dockerfile
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:$PORT/status')" || exit 1
```

### Monitoring with Docker Compose
```bash
# Check service health
docker-compose ps

# View health check logs
docker inspect --format='{{json .State.Health}}' container_name
```

---

## 🔒 Production Considerations

### Security
- Use HTTPS in production
- Configure CORS appropriately
- Set up authentication if needed
- Use environment variables for sensitive data

### Performance
- Use a reverse proxy (nginx) for production
- Enable gzip compression
- Set up load balancing for high traffic
- Monitor resource usage

### Data Persistence
- **Context Data**: Stored in `context_data.json`
- **Docker**: Mount volume for persistence
- **Cloud**: Use persistent storage or database

### Backup Strategy
```bash
# Backup context data
cp context_data.json context_data_backup_$(date +%Y%m%d_%H%M%S).json

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
cp context_data.json "$BACKUP_DIR/context_data_$DATE.json"
find "$BACKUP_DIR" -name "context_data_*.json" -mtime +7 -delete
```

---

## 🚨 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 PID
```

#### Permission Denied (Docker)
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
```

#### Context Data Not Persisting
- Ensure `context_data.json` is writable
- Check Docker volume mounts
- Verify file permissions

### Logs

#### Local Development
```bash
# View server logs
python unified_mcp_server.py --http

# With debug logging
PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from unified_mcp_server import main
main()
"
```

#### Docker
```bash
# View container logs
docker logs container_name

# Follow logs
docker logs -f container_name
```

#### Heroku
```bash
# View logs
heroku logs --tail

# View specific dyno logs
heroku logs --dyno web.1
```

---

## 📈 Scaling

### Horizontal Scaling
```bash
# Docker Compose
docker-compose up --scale mcp-server=3

# Kubernetes
kubectl scale deployment mcp-server --replicas=3
```

### Load Balancing
Use nginx or cloud load balancers to distribute traffic across multiple instances.

### Database Migration
For high-scale deployments, consider migrating from JSON file storage to a proper database like PostgreSQL or MongoDB.

---

## 🎯 Quick Deployment Commands

```bash
# Local development
python unified_mcp_server.py --http

# Docker development
docker-compose up --build

# Docker production
docker-compose --profile production up -d

# Heroku deployment
git push heroku main

# Health check
curl http://localhost:8000/status
```

---

**Need help?** Check the [README](README.md) or [Contributing Guide](CONTRIBUTING.md) for more information.
