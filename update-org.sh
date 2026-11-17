#!/bin/bash

# 📁 update-org.sh - Ordner-Struktur überprüfen & aktualisieren
# ✅ Verwendet: Josef's Organization System
# 🎯 Zweck: Regelmäßig die Ordnerstruktur überprüfen & Abweichungen finden

set -e

HOME_DIR="/home/josef"
ORG_FILE="$HOME_DIR/ORGANIZATION.md"
CHANGELOG_FILE="$HOME_DIR/CHANGELOG.md"

echo "================================"
echo "📁 Ordner-Struktur Überprüfung"
echo "================================"
echo ""

# 1️⃣ Hauptordner-Struktur
echo "✅ HAUPT-ORDNERSTRUKTUR:"
echo ""
ls -lhd "$HOME_DIR"/*/ 2>/dev/null | awk '{print $NF}' | sed "s|$HOME_DIR/||g" | sed 's|/||g'
echo ""

# 2️⃣ Projekte prüfen
echo "✅ AKTIVE PROJEKTE:"
echo ""
ls -d "$HOME_DIR/projects/active"/*/ 2>/dev/null | awk -F'/' '{print $NF}' | sed 's|/$||'
echo ""

# 3️⃣ Auf unerwartete Ordner prüfen
echo "⚠️ UNERWARTETE ORDNER (nicht in Standard-Struktur):"
echo ""

EXPECTED_DIRS="projects|environments|work|tools|media|temp|Archive-cache"

find "$HOME_DIR" -maxdepth 1 -type d ! -name ".*" ! -regex ".*\($EXPECTED_DIRS\)" 2>/dev/null | \
  awk -F'/' '{if (NF > 0) print $NF}' | \
  sed "s|^$||" | \
  grep -v "^$" || echo "(Keine unerwarteten Ordner gefunden)"

echo ""

# 4️⃣ Auf neue Dateien im Home prüfen (sollten nicht sein)
echo "⚠️ DATEIEN IM HOME-VERZEICHNIS (sollten dort nicht sein):"
echo ""

find "$HOME_DIR" -maxdepth 1 -type f ! -name ".*" -newer "$ORG_FILE" 2>/dev/null | \
  awk -F'/' '{print $NF}' || echo "(Keine neuen Dateien gefunden)"

echo ""

# 5️⃣ Größte Ordner
echo "📊 GRÖSSTE ORDNER (Top 5):"
echo ""

du -sh "$HOME_DIR"/*/ 2>/dev/null | sort -hr | head -5 | sed "s|$HOME_DIR/||g"

echo ""

# 6️⃣ Sensitive Daten Prüfung
echo "🔐 SECRETS ÜBERPRÜFUNG:"
echo ""

SECRETS_DIR="$HOME_DIR/work/secrets-backup"
if [ -d "$SECRETS_DIR" ]; then
    echo "⚠️ Secrets gefunden in: $SECRETS_DIR"
    echo "Inhalt:"
    ls -lh "$SECRETS_DIR" 2>/dev/null || echo "(Leer)"
else
    echo "✅ Kein secrets-backup Ordner"
fi

echo ""

# 7️⃣ node_modules im Home (sollte nicht existieren)
if find "$HOME_DIR" -maxdepth 1 -name "node_modules" -type d 2>/dev/null | grep -q .; then
    echo "❌ ERROR: node_modules im Home gefunden! (sollte nicht sein)"
else
    echo "✅ Kein node_modules im Home"
fi

echo ""

# 8️⃣ Leere Ordner
echo "🧹 LEERE ORDNER:"
echo ""

find "$HOME_DIR" -maxdepth 3 -type d -empty 2>/dev/null | head -10 | sed "s|$HOME_DIR/||g" || echo "(Keine leeren Ordner)"

echo ""

# 9️⃣ Zusammenfassung
echo "================================"
echo "✅ Überprüfung abgeschlossen!"
echo "================================"
echo ""
echo "📝 Hinweise:"
echo "1️⃣ Unerwartete Ordner überprüfen & in richtige Struktur verschieben"
echo "2️⃣ Neue Dateien im Home → in entsprechende Ordner verschieben"
echo "3️⃣ Secrets überprüfen & regenerieren falls nötig"
echo "4️⃣ Leere Ordner löschen: rm -rf <ordner>"
echo ""
echo "Nach Änderungen:"
echo "🔄 ORGANIZATION.md aktualisieren"
echo "🔄 CHANGELOG.md aktualisieren"
echo "🔄 In Git committen (wenn vorhanden)"
echo ""
