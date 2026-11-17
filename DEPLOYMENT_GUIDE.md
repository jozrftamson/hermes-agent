# Unified Multi-Platform Configuration

## 🚀 NVIDIA NIM (GPU-beschleunigte Inferenz)

### Setup
```bash
export NVIDIA_API_KEY="your-nvidia-api-key"
export NVIDIA_API_URL="https://api.nvidia.com/v1"
```

### Features
- ✅ Optimiert für NVIDIA GPUs
- ✅ Schnelle Inferenz (405B LLaMA in Millionen Token/s)
- ✅ Pay-per-token Pricing
- ✅ Auto-Scaling
- ✅ Enterprise SLA

### Modelle
- `nvidia/llama-3.1-405b` — Best für komplexe Tasks
- `nvidia/llama-2-70b` — Schneller, günstiger
- Custom fine-tuned models

### Performance
- Latency: ~100-500ms (abhängig von Token)
- Throughput: Millionen Token/sec
- Cost: ~$0.0001-0.001 pro 1K Token

---

## 🤖 Nous Research Portal (Multi-Agent)

### Setup
```bash
export NOUS_API_KEY="your-nous-api-key"
export NOUS_WORKSPACE="my-prompts"
export NOUS_AGENT_COUNT=3
```

### Features
- ✅ Automatische Agent-Orchestrierung
- ✅ Multi-Agent Consensus
- ✅ Open-Source Modelle
- ✅ Hermes Integration
- ✅ Skill-Marketplace

### Agents (Auto-Setup)
- **Agent 1 (Coordinator)**: Plant Tasks, delegiert an andere
- **Agent 2 (Executor)**: Führt Code aus, nutzt Tools
- **Agent 3 (Validator)**: Validiert Ergebnisse, prüft Qualität

### Modelle
- `hermes-3` — Nous' optimiertes Modell
- `llama-3.1-70b` — Open-Source Alternative
- `mistral-7b` — Lightweight Option

---

## 🖥️ Hermes Local (Self-Hosted Development)

### Docker Setup
```bash
docker-compose up hermes hermes-dashboard -d
```

### Features
- ✅ Vollständig lokal
- ✅ Keine API-Keys nötig (Development)
- ✅ Messaging Gateways (Telegram, Discord, etc.)
- ✅ Skill Management
- ✅ Session-Persistierung
- ✅ MCP Server Support

### URL
- API: `http://localhost:9001`
- Dashboard: `http://localhost:9000`

### Konfiguration
```yaml
~/.hermes/config.yaml:
  models:
    - openrouter/openai/gpt-4
    - openrouter/anthropic/claude-3-opus
    - openrouter/nous-research/hermes-3
    - openrouter/meta-llama/llama-3.1-405b
  
  gateways:
    telegram:
      enabled: true
      token: ${TELEGRAM_TOKEN}
    
    discord:
      enabled: true
      token: ${DISCORD_TOKEN}
```

---

## 📊 Unified Client Usage

### Deploy zu allen Plattformen
```python
import asyncio
from unified_client import UnifiedPromptClient, RoutingStrategy

async def main():
    client = UnifiedPromptClient()
    await client.initialize()
    
    # Deploy parallel
    result = await client.deploy_prompt(
        prompt_id="code-review",
        name="Code Security Review",
        system_prompt="Du bist ein Security Expert...",
        category="security",
        tags=["python", "security"],
        strategy=RoutingStrategy.PARALLEL  # Zu allen gleichzeitig
    )
    print(result)

asyncio.run(main())
```

### Execute mit Routing-Strategien

**1. Weighted (bevorzugt NVIDIA)**
```python
result = await client.execute_prompt(
    prompt_id="code-review",
    input_text="...",
    strategy=RoutingStrategy.WEIGHTED  # NVIDIA > Nous > Hermes
)
```

**2. Failover (Fallback-Kette)**
```python
result = await client.execute_prompt(
    prompt_id="code-review",
    input_text="...",
    strategy=RoutingStrategy.FAILOVER  # NVIDIA, wenn fail → Nous, wenn fail → Hermes
)
```

**3. Latency (niedrigste Latenz)**
```python
result = await client.execute_prompt(
    prompt_id="code-review",
    input_text="...",
    strategy=RoutingStrategy.LATENCY  # Automatische Optimierung
)
```

**4. Parallel (alle gleichzeitig)**
```python
result = await client.execute_prompt(
    prompt_id="code-review",
    input_text="...",
    strategy=RoutingStrategy.PARALLEL  # Consensus aus allen
)
```

---

## 🔌 API Endpoints

### Health Status
```bash
# NVIDIA NIM
curl -H "Authorization: Bearer $NVIDIA_API_KEY" \
  https://api.nvidia.com/v1/health

# Nous Portal
curl -H "Authorization: Bearer $NOUS_API_KEY" \
  https://api.nousresearch.com/v1/health

# Hermes Local
curl -H "Authorization: Bearer local-dev-key" \
  http://localhost:9001/health
```

### Execute Prompt
```bash
# Via Unified Client
python3 -c "
import asyncio
from unified_client import UnifiedPromptClient, RoutingStrategy

async def test():
    client = UnifiedPromptClient()
    await client.initialize()
    result = await client.execute_prompt(
        'code-review',
        'def test(): pass',
        RoutingStrategy.WEIGHTED
    )
    print(result)

asyncio.run(test())
"
```

---

## 📈 Performance Comparison

| Metrik | NVIDIA NIM | Nous Portal | Hermes Local |
|--------|-----------|------------|------------|
| Latency | 100-500ms | 200-1000ms | 500-2000ms |
| Throughput | Millionen/s | 1000s/s | 100s/s |
| Cost | $$ (Pay-per-token) | $ (Subscription) | Free |
| GPUs | ✅ NVIDIA H100 | ⚠️ Limited | ❌ Local CPU/GPU |
| Agents | ❌ | ✅ Multi-Agent | ❌ Single |
| Self-Hosted | ❌ | ❌ | ✅ Lokal |

---

## 🔐 Security & Auth

### NVIDIA NIM
```bash
export NVIDIA_API_KEY="nvapi-xxxxx"
# Key-Rotation recommended alle 90 Tage
```

### Nous Portal
```bash
export NOUS_API_KEY="nous-xxxxx"
# Workspace-Level Access Control
```

### Hermes Local
```bash
# No API key needed for development
# Production: Use HERMES_API_KEY environment variable
export HERMES_API_KEY="hermes-secure-key"
```

---

## 🚀 Production Deployment

### Recommended Setup
```
┌─────────────────────────────────────────┐
│       Unified Client (Router)            │
├─────────────────────────────────────────┤
│  Load-Balancing + Health Checks         │
├──────────┬──────────────┬────────────────┤
│NVIDIA NIM│ Nous Portal  │ Hermes Local   │
│(GPU 80%) │(Agent 15%)   │(Backup 5%)     │
└──────────┴──────────────┴────────────────┘
```

### Environment Variables (Production)
```bash
# Create .env.production
NVIDIA_API_KEY=nvapi-xxxxx
NOUS_API_KEY=nous-xxxxx
HERMES_API_KEY=hermes-secure-key
ROUTER_LOG_LEVEL=WARNING
ENABLE_MONITORING=true
GRAFANA_PASSWORD=secure-password
DB_PASSWORD=secure-db-password
```

### Docker Production
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 📊 Monitoring & Metrics

### Prometheus Metrics
```
# Request Count per Platform
unified_requests_total{platform="nvidia_nim"}
unified_requests_total{platform="nous_portal"}
unified_requests_total{platform="hermes"}

# Latency
unified_request_latency_ms{platform="nvidia_nim"}
unified_request_latency_ms{platform="nous_portal"}
unified_request_latency_ms{platform="hermes"}

# Success Rate
unified_success_rate{platform="nvidia_nim"}
unified_success_rate{platform="nous_portal"}
unified_success_rate{platform="hermes"}
```

### View in Grafana
```
http://localhost:3000
- Username: admin
- Password: (from .env)
```

---

## 🆘 Troubleshooting

### NVIDIA NIM Not Responding
```bash
# Prüfe API Key
echo $NVIDIA_API_KEY

# Test Connection
curl -H "Authorization: Bearer $NVIDIA_API_KEY" \
  https://api.nvidia.com/v1/health

# Check Logs
docker-compose logs smart-router | grep "NVIDIA"
```

### Nous Portal Agents Not Starting
```bash
# Check Agent Status
curl -H "Authorization: Bearer $NOUS_API_KEY" \
  https://api.nousresearch.com/v1/agents

# Restart Agents
python3 nous_research_manager.py
```

### Hermes Local Connection Failed
```bash
# Start Services
docker-compose up hermes hermes-dashboard -d

# Wait for startup (30-60s)
sleep 60

# Test Connection
curl http://localhost:9001/health
```

---

## 💰 Cost Optimization

### NVIDIA NIM
- Use smaller models for simple tasks
- Batch requests
- Cache results

### Nous Portal
- Annual subscription > pay-per-request
- Use Hermes for light tasks
- Off-peak scheduling

### Hermes Local
- Fully free (costs only compute)
- Best for development
- Fallback for production

---

## 🎯 Recommended Setup für dich

```bash
# 1. Production (High Traffic)
Strategy: WEIGHTED
- 80% NVIDIA NIM (schnell, kostengünstig)
- 15% Nous Portal (Multi-Agent für komplexe Tasks)
- 5% Hermes (Backup, wenn andere down)

# 2. Development
Strategy: FAILOVER
- Lokal mit Hermes
- Fallback zu Cloud wenn nötig

# 3. Testing
Strategy: PARALLEL
- Test auf allen gleichzeitig
- Vergleiche Ergebnisse
```
