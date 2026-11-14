# Mail Auto-Draft Skill

Auto-draft email replies using Himalaya, Python, and systemd user timers. Designed for safe, whitelist-only email automation with self-reply loop prevention.

## Overview

This skill lets you automatically create draft responses to incoming emails in categories you define (information requests, appointment requests, acknowledgements). It emphasizes safety: drafts are created but **not sent by default**, and auto-send only happens for whitelisted senders and safe categories.

**Key features:**
- ✅ Self-reply loop prevention (never replies to your own addresses)
- ✅ Reply-To-aware recipient selection
- ✅ Whitelist-only sender verification
- ✅ Draft-first, auto-send-optional approach
- ✅ Rate limiting (prevents mail storms)
- ✅ Gmail folder alias support
- ✅ Systemd user timer (runs every 5 minutes)
- ✅ Comprehensive logging

## Requirements

- Linux (uses systemd, `/usr/bin/flock`)
- [Himalaya](https://github.com/soywod/himalaya) CLI configured for your mail account
- Python 3.7+
- systemd user session support

## Installation

1. **Run the setup script:**
   ```bash
   bash setup.sh
   ```

   This installs:
   - `~/.local/bin/process_inbox.py` — processor
   - `~/.config/mail-auto-draft/config.yaml` — configuration
   - `~/.config/systemd/user/mail-auto-draft.service` — systemd service
   - `~/.config/systemd/user/mail-auto-draft.timer` — systemd timer

2. **Configure Himalaya** (if not already done):
   ```bash
   himalaya config create
   # Or edit ~/.config/himalaya/config.toml
   ```

   For Gmail, add folder aliases to prevent SMTP/IMAP mismatches:
   ```toml
   [account.gmail]
   backend = "imap"
   # ... other settings ...

   [account.gmail.folder.aliases]
   sent = "[Gmail]/Sent Mail"
   drafts = "[Gmail]/Drafts"
   trash = "[Gmail]/Trash"
   ```

3. **Edit mail-auto-draft config:**
   ```bash
   nano ~/.config/mail-auto-draft/config.yaml
   ```

   Key settings:
   ```yaml
   own_addresses:
     - "you@gmail.com"
     - "you+auto@gmail.com"

   whitelist_senders:
     - "boss@company.com"
     - "hr@company.com"

   auto_send_enabled: false   # ← KEEP FALSE DURING TESTING
   ```

## Usage

### Test the processor (dry-run mode):
```bash
~/.local/bin/process_inbox.py --dry-run
```

Check logs:
```bash
tail -f ~/.local/share/mail-auto-draft/processor.log
```

### Enable the systemd timer:
```bash
systemctl --user enable mail-auto-draft.timer
systemctl --user start mail-auto-draft.timer
```

### Check timer status:
```bash
systemctl --user status mail-auto-draft.timer
systemctl --user list-timers --all
```

### View service logs:
```bash
journalctl --user -u mail-auto-draft.service -f
```

### Stop the timer:
```bash
systemctl --user stop mail-auto-draft.timer
systemctl --user disable mail-auto-draft.timer
```

## Production Checklist

Before enabling `auto_send_enabled: true`, verify:

- [ ] Himalaya is configured and works (`himalaya mailbox list`)
- [ ] `own_addresses` is set correctly (prevents self-replies)
- [ ] `whitelist_senders` is configured (draft-only for others)
- [ ] Processor runs in dry-run mode without errors
- [ ] Drafts are created for test messages (check Drafts folder)
- [ ] Rate limits are reasonable for your workflow
- [ ] Reply templates are customized if needed
- [ ] Gmail folder aliases are set (if using Gmail)
- [ ] Logs are being written to `~/.local/share/mail-auto-draft/processor.log`
- [ ] Timer runs every 5 minutes (`systemctl --user list-timers`)
- [ ] You've reviewed a few auto-drafted messages before enabling auto-send

## Safety Patterns

### Self-Reply Prevention
The processor maintains a list of your own email addresses and never creates replies to messages from those addresses. This prevents accidental loops if an auto-reply triggers another auto-reply.

```yaml
own_addresses:
  - "you@gmail.com"
  - "you+notifications@gmail.com"
```

### Whitelist-Only Auto-Send
Auto-send is only allowed for senders in the whitelist. All other senders receive draft replies you can review:

```yaml
whitelist_senders:
  - "boss@company.com"
  - "trusted-client@example.com"
auto_send_enabled: false  # Drafts only until you enable this
```

### Reply-To Handling
If the incoming message has a `Reply-To` header, the processor uses that address instead of `From`. This ensures replies go to the correct address (e.g., a team inbox rather than the individual who sent the message).

### Rate Limiting
Prevents accidental mail storms by enforcing per-hour and per-day limits:

```yaml
rate_limit_per_hour: 5
rate_limit_per_day: 20
```

### Gmail Edge Case
Gmail's SMTP can succeed (message sent) but IMAP append to Sent folder can fail. The processor logs this as a warning rather than a fatal error, since the email was actually sent. Gmail folder aliases prevent most of these issues:

```toml
# In ~/.config/himalaya/config.toml
[account.gmail.folder.aliases]
sent = "[Gmail]/Sent Mail"
```

## Troubleshooting

### No drafts created
1. Check logs: `tail -f ~/.local/share/mail-auto-draft/processor.log`
2. Verify Himalaya works: `himalaya message list --mailbox INBOX`
3. Check whitelist: is the sender in the whitelist?
4. Verify own_addresses: is the sender one of your addresses? (would be skipped)

### Timer not running
1. Check status: `systemctl --user status mail-auto-draft.timer`
2. Reload: `systemctl --user daemon-reload`
3. Restart: `systemctl --user restart mail-auto-draft.timer`
4. View timers: `systemctl --user list-timers --all`

### Permission errors
1. Ensure `process_inbox.py` is executable: `chmod 755 ~/.local/bin/process_inbox.py`
2. Check flock: `which flock` (should be `/usr/bin/flock`)
3. Verify directories exist and are writable:
   ```bash
   ls -la ~/.config/mail-auto-draft
   ls -la ~/.local/share/mail-auto-draft
   ```

### Himalaya connection issues
1. Test Himalaya: `himalaya message list --mailbox INBOX`
2. Check config: `cat ~/.config/himalaya/config.toml`
3. Verify Gmail has Himalaya access (if using Gmail, enable "App Passwords")
4. Check authentication: `himalaya account list`

### High CPU usage
1. Reduce timer frequency in `mail-auto-draft.timer` (increase `OnUnitActiveSec`)
2. Check for runaway processes: `ps aux | grep process_inbox`
3. Review logs for errors

## Configuration

Full `config.yaml` options:

```yaml
# Your email addresses (prevents self-replies)
own_addresses:
  - "user@example.com"

# Senders allowed to trigger auto-send
whitelist_senders:
  - "trusted@example.com"

# Enable auto-send (false = drafts only)
auto_send_enabled: false

# Rate limits
rate_limit_per_hour: 5
rate_limit_per_day: 20

# Require manual review of drafts
draft_review_before_send: true

# Logging
log_level: "INFO"
log_file: "~/.local/share/mail-auto-draft/processor.log"

# Himalaya mailbox
mailbox: "INBOX"

# Safe categories (only these trigger auto-reply)
safe_categories:
  - "information_request"
  - "appointment_request"
  - "acknowledgement"

# Custom reply templates
reply_templates:
  information_request: |
    Thank you for your question...
  appointment_request: |
    Thank you for reaching out...
  acknowledgement: |
    Thank you for your message...
```

## Disabling the Skill

```bash
# Stop the timer
systemctl --user stop mail-auto-draft.timer
systemctl --user disable mail-auto-draft.timer

# Remove if desired
rm -rf ~/.config/mail-auto-draft
rm ~/.local/bin/process_inbox.py
rm ~/.config/systemd/user/mail-auto-draft.*
systemctl --user daemon-reload
```

## Security Considerations

1. **Email content is untrusted** — Incoming email is treated as untrusted user input. The processor sanitizes it before using it in prompts or replies.
2. **Prompt injection prevention** — Email content cannot override system instructions or cause unintended actions.
3. **File permissions** — Config files are restricted to user-readable (mode 0600).
4. **Flock mechanism** — `/usr/bin/flock` ensures only one processor runs at a time, preventing race conditions.
5. **Systemd hardening** — The service unit uses `ProtectSystem=strict`, `NoNewPrivileges=true`, and other security options.

## Performance

- **Processor run time**: typically 1-5 seconds per unread message
- **Memory footprint**: ~50-100 MB per run
- **Storage**: ~1 KB per log entry; logs rotate monthly
- **Network**: one IMAP LIST, one per message (READ), one SMTP send if enabled

## Limitations

- Linux-only (requires systemd, flock)
- Requires locally configured Himalaya account
- Category detection is keyword-based (not ML-powered)
- No attachment handling
- No calendar integration for appointment requests
- Rate limiting is per-process (not global across devices)

## Support

Issues, questions, or suggestions? File an issue or see the main Hermes agent documentation.
