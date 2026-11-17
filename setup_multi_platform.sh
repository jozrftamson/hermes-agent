#!/bin/bash

# Multi-Platform Setup Script
# Konfiguriert alle drei Plattformen: NVIDIA NIM, Nous Portal, Hermes

set -e

echo "=========================================="
echo "🚀 Multi-Platform Prompt System Setup"
echo "=========================================="
echo ""

# 1. Environment Setup
echo "1️⃣ Setting up environment..."

if [ ! -f .env.local ]; then
    cat > .env.local << 'EOF'
# NVIDIA NIM
NVIDIA_API_KEY=your-nvidia-api-key-here
NVIDIA_API_URL=https://api.nvidia.com/v1

# Nous Research Portal
NOUS_API_KEY=your-nous-api-key-here
NOUS_WORKSPACE=my-prompts
NOUS_AGENT_COUNT=3

# Hermes Local
HERMES_API_KEY=local-dev-key
HERMES_API_URL=http://localhost:9001

# Database
DB_PASSWORD=secure-password-change-me
GRAFANA_PASSWORD=admin

# Monitoring
PROMETHEUS_RETENTION=15d
EOF
    echo "📝 Created .env.local - Please fill in your API keys!"
    echo "   vim .env.local"
fi

source .env.local

# 2. Voraussetzungen prüfen
echo "2️⃣ Checking prerequisites..."

command -v python3 &> /dev/null || { echo "❌ Python3 required"; exit 1; }
command -v docker &> /dev/null || { echo "❌ Docker required"; exit 1; }

python3 --version
docker --version

# 3. Python Dependencies
echo "3️⃣ Installing Python dependencies..."
pip install -q aiohttp httpx pydantic python-dotenv prometheus-client

# 4. Validiere API Keys
echo "4️⃣ Validating API Keys..."

if [ -z "$NVIDIA_API_KEY" ] || [ "$NVIDIA_API_KEY" = "your-nvidia-api-key-here" ]; then
    echo "⚠️  NVIDIA_API_KEY not configured - skipping NVIDIA NIM"
else
    echo "✅ NVIDIA_API_KEY configured"
fi

if [ -z "$NOUS_API_KEY" ] || [ "$NOUS_API_KEY" = "your-nous-api-key-here" ]; then
    echo "⚠️  NOUS_API_KEY not configured - skipping Nous Portal"
else
    echo "✅ NOUS_API_KEY configured"
fi

# 5. Starte Hermes Local
echo "5️⃣ Starting Hermes Local..."
docker-compose up -d hermes hermes-dashboard postgres prometheus grafana minio
echo "⏳ Waiting for services..."
sleep 15

# 6. Teste Connections
echo "6️⃣ Testing connections..."

echo -n "  Hermes: "
if curl -s http://localhost:9001/health > /dev/null; then
    echo "✅"
else
    echo "❌ (expected on first run)"
fi

echo -n "  Prometheus: "
if curl -s http://localhost:9090 > /dev/null; then
    echo "✅"
else
    echo "❌"
fi

echo -n "  Grafana: "
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅"
else
    echo "❌"
fi

# 7. Initialisiere Unified Client
echo "7️⃣ Testing Unified Client..."
python3 << 'PYTHON_SCRIPT'
import asyncio
import os
from unified_client import UnifiedPromptClient

async def test():
    client = UnifiedPromptClient()
    try:
        await client.initialize()
        print("✅ Unified Client initialized successfully")
        print(f"   Platforms available: {list(client.platforms.keys())}")
        await client.close()
    except Exception as e:
        print(f"⚠️  Some platforms unavailable: {e}")

asyncio.run(test())
PYTHON_SCRIPT

# 8. Deployment Test
echo "8️⃣ Testing deployment..."
python3 << 'PYTHON_SCRIPT'
import asyncio
import json
from unified_client import UnifiedPromptClient, RoutingStrategy

async def test_deploy():
    client = UnifiedPromptClient()
    try:
        await client.initialize()
        
        result = await client.deploy_prompt(
            prompt_id="setup-test",
            name="Setup Test Prompt",
            system_prompt="You are a helpful assistant.",
            category="test",
            tags=["setup", "test"],
            strategy=RoutingStrategy.PARALLEL
        )
        
        print("✅ Deployment test successful")
        print(json.dumps(result, indent=2))
        
        await client.close()
    except Exception as e:
        print(f"⚠️  Deployment test failed: {e}")

asyncio.run(test_deploy())
PYTHON_SCRIPT

# 9. Output Summary
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📊 Access your services:"
echo ""
echo "  🖥️  Hermes Dashboard:"
echo "      http://localhost:9000"
echo ""
echo "  🤖 Hermes API:"
echo "      http://localhost:9001"
echo ""
echo "  📈 Grafana (admin/admin):"
echo "      http://localhost:3000"
echo ""
echo "  📊 Prometheus:"
echo "      http://localhost:9090"
echo ""
echo "  🪣 MinIO S3:"
echo "      http://localhost:9001"
echo ""
echo "💻 Next steps:"
echo ""
echo "  1. Configure API keys in .env.local:"
echo "     - NVIDIA_API_KEY"
echo "     - NOUS_API_KEY"
echo ""
echo "  2. Test deployment:"
echo "     python3 multi_platform_deployer.py"
echo ""
echo "  3. Deploy your prompts:"
echo "     ./deploy.sh"
echo ""
echo "  4. Try the Unified Client:"
echo "     python3 unified_client.py"
echo ""
echo "  5. View logs:"
echo "     docker-compose logs -f"
echo ""
echo "📖 Documentation:"
echo "     cat DEPLOYMENT_GUIDE.md"
echo ""
