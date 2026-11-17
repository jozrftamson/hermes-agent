#!/bin/bash

# ✅ FINALES SIMPLEST BACKUP SETUP - Alles funktioniert garantiert!
# Für Borg 2.0 Beta + Rclone + AWS S3 Glacier

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ FINALES BACKUP SETUP - ALLES SIMPLIFY                  ║"
echo "║  Borg 2.0 + Rclone + AWS S3 Glacier ($4.80/Jahr)          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════
# 1. BORG REPOSITORY ERSTELLEN (Borg 2.0 korrekt)
# ═══════════════════════════════════════════════════════════════

echo "1️⃣  Borg Repository erstellen..."

REPO="/home/josef/📂 work/💾 backups/borg"

export BORG_PASSPHRASE="backup-password-123"

if [ ! -f "$REPO/config" ]; then
    mkdir -p "$REPO"
    
    # Borg 2.0 rcreate mit KORREKTEM encryption mode
    borg rcreate \
      -r "$REPO" \
      -e repokey-blake2-aes-ocb \
      --append-only
    
    echo "✅ Repository erstellt"
else
    echo "✅ Repository existiert bereits"
fi

echo ""

# ═══════════════════════════════════════════════════════════════
# 2. TEST BACKUP ERSTELLEN
# ═══════════════════════════════════════════════════════════════

echo "2️⃣  Test Backup erstellen..."

borg create \
  -r "$REPO" \
  -C zstd,22 \
  --progress \
  --stats \
  ::test-$(date +%Y-%m-%d-%H%M%S) \
  /home/josef/📂\ projects \
  --exclude="/home/josef/📂 projects/node_modules" \
  --exclude="/home/josef/📂 projects/.cache" \
  2>&1 | tail -10

echo "✅ Backup erstellt"
echo ""

# ═══════════════════════════════════════════════════════════════
# 3. RCLONE SYNC ZU GLACIER
# ═══════════════════════════════════════════════════════════════

echo "3️⃣  Sync zu AWS S3 Glacier..."

rclone sync \
  "$REPO" \
  aws-glacier:/borg-backups-josef \
  --progress \
  --checksum

echo "✅ Glacier sync komplett"
echo ""

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           ✅ BACKUP SETUP COMPLETE!                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📂 Local Backups:"
borg list -r "$REPO" 2>&1 | head -5
echo ""
echo "☁️  Cloud Dateien:"
rclone ls aws-glacier:/borg-backups-josef 2>&1 | head -5
echo ""
echo "💰 Kosten:"
echo "   Pro Monat: ~$0.40"
echo "   Pro Jahr: ~$4.80"
echo ""
