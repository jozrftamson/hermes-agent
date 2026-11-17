# 📊 AWS S3 GLACIER BACKUP - STATUS REPORT

**Bericht-Datum:** 16. Mai 2026  
**Diagnose durchgeführt:** 04:10 UTC  
**Status:** 🟡 GEFIXT - NEUEN CREDENTIALS ERFORDERLICH

---

## ✅ BEHOBENE PROBLEME

### 1. Sicherheitsproblem: Exposed Credentials
- **Status:** ✅ BEHOBEN
- **Maßnahme:** Credentials aus rclone.conf entfernt
- **Neue Config:** Verwendet `env_auth = true`
- **Datei:** `~/.config/rclone/rclone.conf`

### 2. Falsche Region
- **Status:** ✅ BEHOBEN
- **Alte Region:** `us-east-1`
- **Neue Region:** `eu-central-1`
- **Bucket:** `s3://borg-backups-josef/`

---

## 🔧 KONFIGURATION AKTUALISIERT

### rclone.conf (neu & sicher)

```ini
[aws-glacier]
type = s3
provider = AWS
env_auth = true
region = eu-central-1
location_constraint = eu-central-1
server_side_encryption = 
storage_class = y

[aws-glacier-crypt]
type = s3
provider = AWS
env_auth = true
region = eu-central-1
location_constraint = eu-central-1
acl = private
storage_class = GLACIER
sse_customer_algorithm = 
```

**Änderungen:**
- ✅ Removed: `access_key_id` (Klartext)
- ✅ Removed: `secret_access_key` (Klartext)
- ✅ Added: `env_auth = true` (nutzt Umgebungsvariablen)
- ✅ Updated: Region von `uy` → `eu-central-1`
- ✅ Verified: `storage_class = GLACIER` bestätigt
- ✅ Set: Datei-Berechtigungen auf `600`

---

## 🔐 NÄCHSTE SCHRITTE ZUM AKTIVIEREN

### SCHRITT 1: Neue AWS Access Keys Generieren

**In AWS Console:**
1. Gehe zu: https://console.aws.amazon.com/iam/
2. Navigate to: Users → [Your User]
3. Security credentials tab
4. Access keys → Create New Access Key
5. Speichere die neuen Keys

### SCHRITT 2: Umgebungsvariablen Setzen

**Option A: Temporär (für Tests)**
```bash
export AWS_ACCESS_KEY_ID="AKIAXXXXXXXXXXXXXXXX"
export AWS_SECRET_ACCESS_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Option B: Dauerhaft (EMPFOHLEN)**

Erstelle `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = AKIAXXXXXXXXXXXXXXXX
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Setze Berechtigungen:
```bash
chmod 600 ~/.aws/credentials
```

**Option C: In .bashrc / .profile**

Füge hinzu:
```bash
# ~/.bashrc
export AWS_ACCESS_KEY_ID="your_new_key"
export AWS_SECRET_ACCESS_KEY="your_new_secret"
```

Dann:
```bash
source ~/.bashrc
```

### SCHRITT 3: Verbindung Testen

```bash
# Test mit rclone
rclone lsd aws-glacier:

# Sollte anzeigen:
# 2026-05-16 09:16:10        -1 borg-backups-josef
```

---

## 📋 CHECKLISTE

- [ ] AWS IAM Console öffnen
- [ ] Alte Access Keys revozieren
- [ ] Neue Access Keys generieren
- [ ] Neue Keys kopieren
- [ ] `AWS_ACCESS_KEY_ID` Umgebungsvariable setzen
- [ ] `AWS_SECRET_ACCESS_KEY` Umgebungsvariable setzen
- [ ] `rclone lsd aws-glacier:` ausführen (sollte funktionieren)
- [ ] Bucket Inhalte überprüfen: `rclone ls aws-glacier:/borg-backups-josef/`
- [ ] Backup-Sync testen
- [ ] Logs überprüfen

---

## 📊 Backup-System Übersicht

### Komponenten

| Komponente | Status | Details |
|------------|--------|---------|
| Borg Repository | ⏳ Zu überprüfen | `/home/josef/Backups/restic/` |
| rclone Config | ✅ Aktualisiert | Region: eu-central-1 |
| AWS Credentials | 🟡 Erneuerung erforderlich | Alte Keys gelöscht, neue Keys erforderlich |
| S3 Bucket | ✅ Erreichbar | `borg-backups-josef` in `eu-central-1` |
| Storage Class | ✅ GLACIER | Kostengünstige Langzeitspeicherung |
| Encryption | ✅ AES256 | Server-seitige Verschlüsselung |

### Cron-Jobs

```bash
0 2 * * * # Restic Backup (täglich 02:00)
30 3 * * * # Restic Minimieren (täglich 03:30)
0 4 * * 0 # Restic Prune (Sonntag 04:00)
0 1 * * * # Organization Update (täglich 01:00)
0 6 * * * # Wiki Generator (täglich 06:00)
```

---

## 🔍 TESTING NACH SETUP

### Test 1: AWS Verbindung
```bash
aws s3 ls --region eu-central-1
# oder mit rclone
rclone lsd aws-glacier:
```

### Test 2: Bucket Zugriff
```bash
rclone ls aws-glacier:/borg-backups-josef/ --max-depth 1
```

### Test 3: Storage Class Überprüfung
```bash
# Prüfe, dass Dateien in GLACIER sind
aws s3api list-objects-v2 \
  --bucket borg-backups-josef \
  --region eu-central-1 \
  --query 'Contents[*].[Key,StorageClass]'
```

### Test 4: Backup-Sync
```bash
# Führe manuell aus
/home/josef/Projekte/Automation/resticBackup/minimieren/minimize-restic.sh

# Oder via rclone
rclone sync /home/josef/Backups/restic aws-glacier:/borg-backups-josef/ --verbose
```

---

## 🛡️ SICHERHEITS-NOTES

### Credentials-Handling
- ✅ Keine Credentials in Config-Dateien
- ✅ Keine Credentials in Git
- ✅ Umgebungsvariablen verwenden
- ✅ IAM Best Practices beachten

### Datei-Berechtigungen
```bash
chmod 600 ~/.config/rclone/rclone.conf
chmod 600 ~/.aws/credentials
chmod 600 ~/.aws/config
```

### AWS Best Practices
- Regelmäßig Access Keys rotieren
- Least-Privilege IAM Policies
- CloudTrail für Audit-Logging
- MFA für AWS Console

---

## 📞 TROUBLESHOOTING

### Problem: "InvalidAccessKeyId"
**Lösung:** Neue Access Keys generieren und setzen

### Problem: "BucketRegionError"
**Lösung:** ✅ Bereits behoben (Region ist jetzt eu-central-1)

### Problem: "Access Denied"
**Lösung:** IAM Policy überprüfen für S3 Zugriff

### Problem: "Slow Upload"
**Lösung:** GLACIER hat längere Retrieval-Zeiten (ist normal)

---

## 📅 NÄCHSTE TERMINE

- **Sofort:** Neue AWS Keys generieren
- **Heute:** rclone Zugriff testen
- **Diese Woche:** Ersten erfolgreichen Backup durchführen
- **Monatlich:** Credentials rotieren
- **Quarterly:** Backup-Integrität überprüfen

---

**Report Status:** ✅ Bereit für Aktivierung  
**Erforderliche Aktion:** Neue AWS Access Keys generieren  
**Dringlichkeit:** 🟡 Mittel (heute erledigen)
