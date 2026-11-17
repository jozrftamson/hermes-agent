#!/bin/bash

# Multi-Platform Deployment & Testing Script

set -e

echo "🚀 Multi-Platform Prompt Deployment System"
echo "=========================================="
echo ""

# Konfiguration
export NVIDIA_API_KEY="${NVIDIA_API_KEY:-your-nvidia-key}"
export NOUS_API_KEY="${NOUS_API_KEY:-your-nous-key}"
export HERMES_API_KEY="${HERMES_API_KEY:-your-hermes-key}"
export DB_PASSWORD="${DB_PASSWORD:-prompts123}"

# 1. Prüfe Voraussetzungen
echo "✅ Checking prerequisites..."
command -v docker &> /dev/null || { echo "❌ Docker required"; exit 1; }
command -v python3 &> /dev/null || { echo "❌ Python3 required"; exit 1; }

# 2. Erstelle Verzeichnisse
echo "📁 Creating directories..."
mkdir -p prompts/exports
mkdir -p grafana/provisioning/{dashboards,datasources}
mkdir -p router_logs

# 3. Kompiliere Prompts
echo "🔧 Compiling prompts..."
python3 scripts/prompt_compiler.py

# 4. Starte Docker-Compose
echo "🐳 Starting Docker containers..."
docker-compose up -d

# 5. Warte auf Services
echo "⏳ Waiting for services to be ready..."
sleep 10

echo "🏥 Checking health status..."
curl -s http://localhost:8080/health | python3 -m json.tool

# 6. Deploye Prompts
echo "🚀 Deploying prompts to all platforms..."
python3 multi_platform_deployer.py

# 7. Test Router
echo "🧪 Testing Smart Router..."
curl -s -X POST http://localhost:8080/prompts/execute \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_id": "code-review",
    "input": "def test(): pass"
  }' \
  -G -d "strategy=weighted" | python3 -m json.tool

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Access points:"
echo "  - Smart Router:     http://localhost:8080"
echo "  - Hermes Dashboard: http://localhost:9000"
echo "  - Hermes API:       http://localhost:9001"
echo "  - Grafana:          http://localhost:3000 (admin/admin)"
echo "  - Prometheus:       http://localhost:9090"
echo "  - MinIO:            http://localhost:9001"
echo "  - PostgreSQL:       localhost:5432"
echo ""
echo "📝 View logs:"
echo "  docker-compose logs -f smart-router"
echo "  docker-compose logs -f hermes"
echo ""
