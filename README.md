# 🚀 Multi-Platform Prompt Deployment System

Automatisches Deployment von Prompts zu **NVIDIA NIM**, **Nous Research Portal** und **Hermes** — alles aus einer einzigen Quelle.

## 📊 Architektur

```
┌─────────────────────────────────────────────────────────┐
│           Mitwirkende schreiben Prompts                 │
│           (prompts/xyz/prompt.md)                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Prompt Compiler     │
          │ (validate + compile) │
          └──────┬───────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│NVIDIA  │  │ Nous   │  │Hermes  │
│ NIM    │  │Portal  │  │Local   │
└────────┘  └────────┘  └────────┘
    │            │            │
    └────────────┼────────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │   Smart Router       │
      │  (Load-Balancing &   │
      │   Failover Logic)    │
      └──────────────────────┘
```

## 🚀 Quick Start

### 1. Systemvoraussetzungen
```bash
# Installiere Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Python 3.11+
python3 --version
```

### 2. Environment Setup
```bash
# Clone Projekt
git clone <your-repo>
cd prompts-deployment

# Erstelle .env
cat > .env << 'EOF'
NVIDIA_API_KEY=your-nvidia-key
NOUS_API_KEY=your-nous-key
HERMES_API_KEY=your-hermes-key
DB_PASSWORD=secure-password
GRAFANA_PASSWORD=admin
MINIO_USER=minioadmin
MINIO_PASSWORD=minioadmin
EOF

chmod 600 .env
```

### 3. Starte System
```bash
chmod +x deploy.sh
./deploy.sh
```

Das startet automatisch:
- 🔵 **Hermes** (Local Development)
- 🟦 **Smart Router** (API Gateway)
- 🟨 **PostgreSQL** (Datenbank)
- 📊 **Prometheus** + **Grafana** (Monitoring)
- 🪣 **MinIO** (S3-Storage)

## 📝 Contributor-Workflow

### Schritt 1: Neuen Prompt erstellen

```bash
mkdir -p prompts/mein-prompt/
cat > prompts/mein-prompt/prompt.md << 'EOF'
# Mein Prompt

**Category:** code-review
**Version:** 1.0
**Tags:** python, security
**Model:** claude-opus

## Beschreibung
Analysiert Code auf Sicherheitslücken.

## System Prompt
```
Du bist ein Security Expert...
```

## Beispiel Input
```python
def unsafe_code():
    pass
```

## Beispiel Output
```
Keine Probleme gefunden.
```
EOF
```

### Schritt 2: Commit & Push
```bash
git add prompts/mein-prompt/
git commit -m "Add: Security code review prompt"
git push origin feature/my-prompt
```

### Schritt 3: Pull Request
- GitHub Actions lädt automatisch
- Validiert den Prompt
- Deployt zu allen Plattformen
- Erstellt Release-Notes

## 🔌 API Endpoints

### Smart Router

**Health Check:**
```bash
curl http://localhost:8080/health
```

**Execute Prompt (Weighted Load-Balancing):**
```bash
curl -X POST http://localhost:8080/prompts/execute \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_id": "code-review",
    "input": "def test(): pass"
  }' \
  -G -d "strategy=weighted"
```

**Execute mit Fallback:**
```bash
curl -X POST http://localhost:8080/prompts/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt_id": "code-review", "input": "..."}' \
  -G -d "strategy=fallback"
```

**Routing Strategien:**
- `weighted` — Gewichtete Auswahl (NVIDIA > Nous > Hermes)
- `round_robin` — Rotierend (Least Requests First)
- `random` — Zufällig
- `fallback` — Nur Fallback (erste verfügbare, dann nächste)
- `all` — Alle Plattformen parallel

### Hermes API

```bash
# Health
curl http://localhost:9001/health

# Execute Prompt
curl -X POST http://localhost:9001/prompts/execute \
  -H "Authorization: Bearer $HERMES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt_id": "code-review", "input": "..."}'
```

## 📊 Monitoring & Dashboards

| URL | Purpose |
|-----|---------|
| `http://localhost:3000` | Grafana (dashboards) |
| `http://localhost:9090` | Prometheus (metrics) |
| `http://localhost:9000` | Hermes Dashboard |
| `http://localhost:9001` | MinIO Console |
| `http://localhost:5432` | PostgreSQL |

**Grafana Login:**
- Username: `admin`
- Password: (from `.env` `GRAFANA_PASSWORD`)

## 📡 Deployment-Strategien

### Option 1: Nur Hermes (Lokal)
```bash
docker-compose up hermes smart-router
```

### Option 2: Hermes + Cloud
```bash
docker-compose up -d
# Konfiguriere NVIDIA_API_KEY & NOUS_API_KEY in .env
```

### Option 3: Production Multi-Region
```bash
# Deploy zu multiple regions mit Terraform/Helm
terraform apply -var "region=us-west-2"
```

## 🔐 Security Best Practices

### Secrets Management
```bash
# Speichere API Keys in GitHub Secrets (nicht in .env!)
# GitHub → Settings → Secrets and variables → Actions

NVIDIA_API_KEY
NOUS_API_KEY
HERMES_API_KEY
DB_PASSWORD
```

### Network Isolation
```bash
# Hermes nur auf localhost
# Smart Router mit Auth-Header geschützt
# PostgreSQL in private network
```

### Backup & Recovery
```bash
# MinIO S3-compatible backup
docker exec minio-storage mc cp --recursive \
  prompts-db s3/backups/

# Database backup
docker exec prompt-db pg_dump -U prompts prompts_db > backup.sql
```

## 🐛 Troubleshooting

### Smart Router nicht erreichbar
```bash
docker-compose logs smart-router
curl http://localhost:8080/health
```

### Hermes API fehler
```bash
docker-compose logs hermes
# Prüfe HERMES_API_KEY in .env
```

### Database connection failed
```bash
docker-compose logs postgres
docker exec prompt-db psql -U prompts -d prompts_db -c "SELECT 1;"
```

### Deployment fehlgeschlagen
```bash
# Prüfe Health
curl http://localhost:8080/health

# Logs ansehen
docker-compose logs -f multi-deployer

# Manuell retry
python3 multi_platform_deployer.py
```

## 📚 Weitere Ressourcen

- [Hermes Dokumentation](https://hermes-agent.nousresearch.com/docs)
- [NVIDIA NIM API](https://docs.nvidia.com/nim)
- [Nous Research Portal](https://portal.nousresearch.com)
- [Smart Router Dokumentation](./smart_router.py)

## 🤝 Contribution

1. Fork das Repo
2. Feature Branch: `git checkout -b feature/new-prompt`
3. Schreibe nur `prompts/xyz/prompt.md`
4. Commit: `git commit -m "Add: Description"`
5. Push: `git push origin feature/new-prompt`
6. Pull Request öffnen
7. GitHub Actions deployt automatisch ✨

## 📄 Lizenz

MIT License — siehe LICENSE Datei

## 🆘 Support

- GitHub Issues: https://github.com/your-repo/issues
- Email: support@example.com
- Discord: https://discord.gg/yourserver
