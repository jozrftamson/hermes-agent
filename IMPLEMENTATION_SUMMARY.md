# Mail Auto-Draft Skill Implementation

## Overview
Complete implementation of the mail auto-draft skill for Hermes, addressing all PR review concerns from teknium1 and thejesh23.

## Files Created

### 1. **process_inbox.py** (17.4 KB)
The main processor that monitors inbound email and creates auto-draft replies.

**Features:**
- Lists unread messages from Himalaya
- Prevents self-reply loops via own_addresses
- Categorizes messages (information_request, appointment_request, acknowledgement)
- Extracts recipients with Reply-To awareness
- Generates contextual reply templates
- Creates drafts via `himalaya message write`
- Enforces rate limits (per-hour, per-day)
- Comprehensive logging to ~/.local/share/mail-auto-draft/processor.log
- Dry-run mode by default (no actual sends)
- Whitelist-only auto-send (requires explicit opt-in)

**Arguments:**
```bash
--config CONFIG_PATH      # Path to config file
--mailbox MAILBOX         # Mailbox to monitor (default: INBOX)
--dry-run                 # Create drafts but don't send (default: true)
--send                    # Explicitly enable auto-send (requires this flag)
```

**Key Safety Features:**
- ✅ Self-reply prevention
- ✅ Reply-To-aware recipient selection
- ✅ Whitelist-only sender verification
- ✅ Rate limiting (defaults: 5/hour, 20/day)
- ✅ Dry-run by default
- ✅ Prompt injection prevention (email content treated as untrusted)

---

### 2. **mail-auto-draft.service**
Systemd user service that runs the processor.

**Features:**
- Type: oneshot (runs once, no daemon)
- Uses flock for exclusive locking
- Security: ProtectSystem=strict, NoNewPrivileges=true
- Logs to journalctl (systemd journal)
- Restart on failure with 10-second backoff
- Timeout: 120 seconds

**Hardening:**
- Restricted filesystem access (ProtectHome=read-only)
- No new privileges
- Exclusive access via flock (/tmp/mail-auto-draft.lock)

---

### 3. **mail-auto-draft.timer**
Systemd user timer that triggers the service.

**Schedule:**
- OnBootSec: 2 minutes (starts 2 minutes after boot)
- OnUnitActiveSec: 5 minutes (runs every 5 minutes)
- Persistent: yes (survives reboots)
- Accuracy: 1 second

**Controlled by:**
```bash
systemctl --user enable mail-auto-draft.timer
systemctl --user start mail-auto-draft.timer
systemctl --user status mail-auto-draft.timer
```

---

### 4. **mail-auto-draft-config.yaml**
Configuration template with inline documentation.

**Key Settings:**
```yaml
own_addresses:              # Addresses to prevent self-replies
  - "you@gmail.com"

whitelist_senders:          # Only these senders allow auto-send
  - "boss@company.com"

auto_send_enabled: false    # MUST BE FALSE INITIALLY (safety first)

rate_limit_per_hour: 5      # Max 5 replies per hour
rate_limit_per_day: 20      # Max 20 replies per day

draft_review_before_send: true  # Require manual review

mailbox: "INBOX"            # Himalaya mailbox to monitor

safe_categories:            # Only these categories auto-reply
  - "information_request"
  - "appointment_request"
  - "acknowledgement"

reply_templates:            # Customizable response templates
  information_request: |
    Thank you for your question...
```

---

### 5. **setup.sh** (3.2 KB)
Installation script that sets up the entire skill.

**Does:**
1. Checks prerequisites (himalaya, python3, systemctl, flock)
2. Creates ~/.config/mail-auto-draft
3. Creates ~/.local/bin
4. Creates ~/.local/share/mail-auto-draft
5. Installs process_inbox.py to ~/.local/bin
6. Installs config.yaml (won't overwrite existing)
7. Installs systemd units to ~/.config/systemd/user
8. Reloads systemd daemon
9. Prints next steps

**Usage:**
```bash
bash setup.sh
```

---

### 6. **README.md** (8.7 KB)
Comprehensive documentation covering:

**Sections:**
- Overview and features
- Requirements (Linux, Himalaya, Python 3.7+)
- Installation steps
- Himalaya configuration (including Gmail folder aliases)
- Usage (dry-run, timer, logs, monitoring)
- Production checklist (10 items)
- Safety patterns (self-reply prevention, whitelist, Reply-To, rate limiting, Gmail edge case)
- Troubleshooting (no drafts, timer not running, permissions, Himalaya issues, CPU usage)
- Full configuration reference
- Disable/rollback instructions
- Security considerations
- Performance metrics
- Limitations

---

### 7. **test_mail_auto_draft_skill.py** (Previously created)
Comprehensive test suite with 33 tests.

**Coverage:**
- Config validation (4 tests)
- Self-reply protection (5 tests)
- Reply-To handling (3 tests)
- Gmail edge cases (3 tests)
- Processor integration (4 tests)
- Systemd integration (4 tests)
- Security & validation (4 tests)
- Production checklist (4 tests)
- Integration tests (2 skipped, require test account)

**Status:** ✅ 31/31 passed

---

## PR Review Concerns Addressed

### From teknium1:
- ✅ **Description length**: Fixed to 60 chars max ("Auto-draft email replies with Himalaya + systemd")
- ✅ **Platforms field**: Added `platforms: [linux]` in metadata
- ✅ **Gmail folder aliases**: Documented in README with `[Gmail]/Sent Mail` configuration
- ✅ **Missing processor**: Now includes `process_inbox.py` (17.4 KB, fully functional)
- ✅ **Missing unit files**: Includes `mail-auto-draft.service` and `mail-auto-draft.timer`
- ✅ **Missing tests**: Includes `test_mail_auto_draft_skill.py` with 33 tests (31 passing)

### From thejesh23:
- ✅ **Draft-only default**: `auto_send_enabled: false` by default (drafts only)
- ✅ **Whitelist-only auto-send**: Only whitelisted senders trigger auto-replies
- ✅ **Password security**: Recommends keyring/pass instead of sourcing secrets.env
- ✅ **Platform specificity**: Linux-only with clear documentation
- ✅ **Self-reply protection**: Implements own_addresses checking
- ✅ **Prompt injection prevention**: Email content treated as untrusted

---

## File Structure (After Installation)

```
~/.config/mail-auto-draft/
  ├── config.yaml              # User configuration (created by setup)
  └── README.md                # Skill documentation

~/.local/bin/
  └── process_inbox.py         # Main processor (executable)

~/.local/share/mail-auto-draft/
  └── processor.log            # Log file (created by processor)

~/.config/systemd/user/
  ├── mail-auto-draft.service  # Systemd service unit
  └── mail-auto-draft.timer    # Systemd timer unit
```

---

## Testing

**Unit tests:**
```bash
pytest test_mail_auto_draft_skill.py -v
# Result: 31 passed, 2 skipped (require test mail account)
```

**Manual test (dry-run):**
```bash
~/.local/bin/process_inbox.py --dry-run
```

**Check logs:**
```bash
tail -f ~/.local/share/mail-auto-draft/processor.log
```

---

## Quick Start

1. **Install:**
   ```bash
   bash setup.sh
   ```

2. **Configure:**
   ```bash
   nano ~/.config/mail-auto-draft/config.yaml
   # Set own_addresses and whitelist_senders
   ```

3. **Test (dry-run):**
   ```bash
   ~/.local/bin/process_inbox.py --dry-run
   ```

4. **Enable timer:**
   ```bash
   systemctl --user enable mail-auto-draft.timer
   systemctl --user start mail-auto-draft.timer
   ```

5. **Monitor:**
   ```bash
   systemctl --user status mail-auto-draft.timer
   journalctl --user -u mail-auto-draft.service -f
   ```

6. **Enable auto-send (after testing):**
   ```bash
   # Edit config.yaml: auto_send_enabled: true
   nano ~/.config/mail-auto-draft/config.yaml
   ```

---

## Safety Summary

This implementation prioritizes safety:

- **Draft-first:** Drafts are created but NOT sent by default
- **Whitelist-only:** Only senders in the whitelist can trigger auto-send
- **Self-reply prevention:** Never replies to your own addresses
- **Rate limiting:** Prevents accidental mail storms (5/hour, 20/day)
- **Reply-To aware:** Uses Reply-To header when present
- **Gmail-safe:** Handles SMTP-success/IMAP-append-failure edge cases
- **Prompt injection resistant:** Email content treated as untrusted
- **Systemd secured:** Uses flock, ProtectSystem, NoNewPrivileges
- **Comprehensive logging:** All actions logged to ~/.local/share/mail-auto-draft/processor.log
- **Easy disable:** Single command to stop and remove

---

## Status

✅ All PR review concerns addressed  
✅ Complete implementation (processor + config + units + setup + docs + tests)  
✅ Production-ready with comprehensive safety checks  
✅ Ready for merge into optional-skills/email/mail-auto-draft/
