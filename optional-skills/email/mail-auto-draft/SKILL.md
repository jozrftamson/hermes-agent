---
name: mail-auto-draft
description: Auto-reply to inbound email via Himalaya
version: 1.0.0
author: jozrftamson
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [email, himalaya, imap, smtp, automation, systemd, gmail]
    category: email
prerequisites:
  commands: [himalaya, python3, systemctl]
  python_packages: [pyyaml, requests]
---

# Mail Auto-Draft with Himalaya

Build a practical local inbound email automation workflow that:
- reads new mail from INBOX via Himalaya
- classifies simple inbound requests
- automatically replies only to safe standard cases
- avoids self-reply loops
- runs continuously via systemd user timers

This skill is intentionally optional. It is highly useful for users who want mailbox automation, but it depends on local mail account setup, machine-specific deployment choices, and provider-specific operational details.

## Security Model

### Untrusted Input
Treat all inbound email content (sender, headers, body) as untrusted by default:
- Validate sender against `own_addresses` whitelist
- Parse headers strictly (no format assumptions)
- Sanitize body before classification
- Never log raw email bodies to production logs
- Use allowlist-only auto-send, never blocklist-based allow

### Default Modes
- **Draft mode first**: `--mode draft` generates replies without sending
- **Auto mode only after review**: `--mode auto` sends only whitelisted categories
- **Whitelist-only**: Never auto-send uncertain or sensitive categories
- **Rate limiting**: systemd timer runs once per 60s (OnUnitActiveSec=60s)
- **Self-reply protection**: Ignore mail from `own_addresses`

### Forbidden Categories
These are never auto-sent, remain draft-only:
- `sensibel` (sensitive/personal)
- `individuell` (individual/specific)
- `unklar` (unclear)
- `ignorieren` (ignore)

## When to Use

Use this skill when the user wants to automate replies to inbound email on their own mailbox, especially on Ubuntu/Linux with Himalaya.

Typical requests:
- "Automatically answer simple incoming emails"
- "Set up a local email auto-responder with Gmail and Himalaya"
- "Keep it running in the background every minute"
- "Make it safe enough for production"

This skill is for user-owned mailboxes, not agent-owned inboxes like AgentMail.

## Quick Reference

Typical flow:
1. configure Himalaya for the mailbox
2. create or adapt `process_inbox.py` and `config.yaml`
3. test in draft mode
4. enable auto-send only for safe whitelisted categories
5. run continuously with a `systemd --user` timer

## Requirements

1. Himalaya CLI installed and configured
2. Python 3.8+ with `pyyaml` and `requests`
3. A working IMAP/SMTP account in `~/.config/himalaya/config.toml`
4. Linux with systemd (this skill requires `systemd --user` and `/usr/bin/flock`)
5. A local project directory containing:
   - `process_inbox.py`
   - `config.yaml`
   - `prompts/system_prompt.txt`
   - `prompts/user_prompt.txt`

## Recommended Project Files

Minimum structure:
- `process_inbox.py` ✅ (provided by this skill)
- `config.yaml` (user creates from `config.example.yaml`)
- `config.example.yaml` ✅ (provided)
- `README.md`
- `deploy/systemd/mail-auto-draft.service` ✅ (provided)
- `deploy/systemd/mail-auto-draft.timer` ✅ (provided)
- `prompts/system_prompt.txt` ✅ (provided)
- `prompts/user_prompt.txt` ✅ (provided)

Local runtime dirs (created by `process_inbox.py`):
- `drafts/` — generated reply drafts
- `logs/` — `mail_actions.jsonl` action log
- `data/` — persistent state
- `runtime/` — lock files

## Safe Defaults

For production, prefer:
- `require_unseen: true`
- `require_new_in_inbox: true`
- `require_whitelist: true`
- `require_high_confidence: true`
- `confidence_threshold` around `70` to `85`
- `forbid_sensitive_categories` includes all four above
- Start in `mode: draft` until you've reviewed 10+ generated replies

## Critical Safety Rules

### 1. Always define own addresses

In `config.yaml`:

```yaml
own_addresses:
  - your-address@example.com
```

This prevents self-reply loops when your own replies appear in INBOX.

### 2. Prefer Reply-To over From

When selecting the reply recipient, `process_inbox.py` implements:
1. use `Reply-To` if present and valid
2. otherwise use `From`
3. if the reply template has empty `To:`, reject before sending

### 3. Ignore own-sender mail

Any inbound mail whose sender matches `own_addresses` is ignored with reason `self_sender`.

### 4. Do not auto-send uncertain categories

Keep these as draft-only or blocked:
- `sensibel`
- `individuell`
- `unklar`
- `ignorieren`

### 5. Gmail Sent Folder Configuration

On Gmail, configure `folder.aliases` in `~/.config/himalaya/config.toml` BEFORE relying on sent-mail handling:

```toml
folder.aliases = { sent = "[Gmail]/Sent Mail" }
```

Reference: [skills/email/himalaya/references/configuration.md:86–94](https://github.com/NousResearch/hermes-agent/blob/main/skills/email/himalaya/references/configuration.md#L86)

If SMTP succeeds but IMAP append to Sent fails on Gmail, you may see:
- `cannot add IMAP message`
- `Folder doesn't exist`

This is a known Gmail behavior. Verify recipient delivery before resending.

## Himalaya Config Notes

For Gmail, use an app password, not the normal password.

### Secure Password Storage (Recommended)

Use systemd user keyring or a local encrypted store. **Do NOT source shell profiles in auth commands** (`sh -lc '. secrets.env'` is insecure).

**Option A: systemd user keyring (recommended)**

```bash
secret-tool store --label="Gmail App Password" email my-account@gmail.com
```

Then in `~/.config/himalaya/config.toml`:

```toml
backend.auth.cmd = "secret-tool lookup email my-account@gmail.com"
message.send.backend.auth.cmd = "secret-tool lookup email my-account@gmail.com"
```

**Option B: Local encrypted file** (if keyring unavailable)

```bash
mkdir -p ~/.config/mail-auto-draft/
chmod 700 ~/.config/mail-auto-draft/
echo "YOUR_APP_PASSWORD" > ~/.config/mail-auto-draft/.app_password
chmod 600 ~/.config/mail-auto-draft/.app_password
```

Then in `~/.config/himalaya/config.toml`:

```toml
backend.auth.cmd = "cat ~/.config/mail-auto-draft/.app_password"
message.send.backend.auth.cmd = "cat ~/.config/mail-auto-draft/.app_password"
```

⚠️ Avoid sourcing shell profiles in authentication commands. Use keyring or a dedicated secret file.

## Continuous Background Processing

Prefer a `systemd --user` oneshot service plus timer over an infinite Python loop. This skill provides pre-built unit files:

- `deploy/systemd/mail-auto-draft.service` — runs `process_inbox.py` once
- `deploy/systemd/mail-auto-draft.timer` — triggers the service every 60s

The service uses `/usr/bin/flock` to prevent concurrent runs.

## Procedure

### 1. Verify dependencies

```bash
himalaya --version
python3 -c "import yaml, requests; print('OK')"
python3 -m py_compile process_inbox.py
```

### 2. Configure Himalaya

Ensure `~/.config/himalaya/config.toml` is set up with your IMAP/SMTP account and includes folder aliases for Gmail:

```toml
folder.aliases = { sent = "[Gmail]/Sent Mail" }
```

Test it:

```bash
himalaya list INBOX --limit 1
```

### 3. Create config.yaml from template

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings:
# - own_addresses: your email(s)
# - whitelist_categories: only auto-reply to these
# - forbid_sensitive_categories: stay draft-only
```

### 4. Test in draft mode first

```bash
python3 process_inbox.py --mode draft --limit 5
```

Review:
- generated drafts in `drafts/` (if configured)
- `logs/mail_actions.jsonl` for action log

### 5. Switch to auto mode only after review

```bash
python3 process_inbox.py --mode auto --limit 1
```

Verify replies are sent only to safe categories.

### 6. Enable timer-based background processing

Install the systemd units (adjust `WorkingDirectory` path in `.service` file if needed):

```bash
# Copy units to user systemd dir
mkdir -p ~/.config/systemd/user/
cp deploy/systemd/mail-auto-draft.* ~/.config/systemd/user/

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable --now mail-auto-draft.timer
```

## Useful Runtime Commands

Status:

```bash
systemctl --user status mail-auto-draft.timer --no-pager
systemctl --user status mail-auto-draft.service --no-pager
```

Logs:

```bash
journalctl --user -u mail-auto-draft.service -n 50 --no-pager
```

Manual run:

```bash
python3 process_inbox.py --limit 1
```

Stop the timer:

```bash
systemctl --user stop mail-auto-draft.timer
```

## Example Workflow

Example use case:
- a user wants automatic replies for simple inbound messages such as information requests, lightweight appointment requests, or simple acknowledgements
- Hermes helps configure Himalaya and the local processing script
- the workflow only auto-sends safe standard categories
- anything uncertain stays as draft for manual review

Expected log output:

```
2026-11-21T10:15:42 - INFO - Processing 3 messages in draft mode
2026-11-21T10:15:42 - INFO - [msg-123] Reply to user@example.com: Re: What is your process? (info_request)
2026-11-21T10:15:43 - INFO - [DRAFT] Reply to user@example.com: Re: What is your process?
```

## Layered Security with EMAIL_SUPPRESS_OUTBOUND

If running alongside a Hermes gateway instance, you can add an extra safety layer by setting:

```bash
export EMAIL_SUPPRESS_OUTBOUND=true
```

This disables SMTP sends from the built-in `EmailAdapter` (if that feature is available in your version). This ensures your Himalaya-based workflow is the sole email egress path when running parallel gateway instances. See [feat(gateway): add EMAIL_SUPPRESS_OUTBOUND kill switch #5717](https://github.com/NousResearch/hermes-agent/pull/5717) for details (note: this is a proposed design; check the hermes-agent repo for current support).

## Troubleshooting

### It replies to itself repeatedly
Check:
- `own_addresses` is configured correctly
- self-sender mail is ignored in logs (reason: `self_sender`)
- only new/unseen mail is processed (`require_unseen: true`)
- review `logs/mail_actions.jsonl` for all actions

### Replies go to the wrong recipient
Check:
- recipient selection prefers `Reply-To`
- fallback uses `From`
- verify headers in logs:
  ```bash
  himalaya read <msg_id> --headers
  ```

### It sends to newsletters or bulk mail
Tighten:
- subject keyword filters in `classify_inbound_request()`
- header ignore rules
- whitelist-only auto-send (`require_whitelist: true`)
- high confidence requirement (`confidence_threshold: 85`)

### Himalaya says send failed but recipient got the email
This is often the Gmail IMAP append issue after SMTP success.
- Check Gmail's Sent Mail folder manually
- Review Himalaya logs: `journalctl -xe`
- Verify `folder.aliases` is configured for Gmail

### No messages processed
Check:
- `himalaya list INBOX` returns messages
- `require_unseen: true` — new messages must be unseen
- message count not hitting rate limits
- logs: `journalctl --user -u mail-auto-draft.service`

## Testing

This skill includes unit tests covering:
- Reply-To vs From recipient selection
- Self-reply protection (`own_addresses` matching)
- Email classification (info request, appointment, acknowledgment)
- Email validation and format checking
- Untrusted input handling (no code execution, injection safety)

Run tests:

```bash
pytest tests/skills/test_mail_auto_draft_skill.py -v
```

All 15+ tests should pass. Tests are included as AGENTS.md:942-950 compliance requirement.

## Verification

A successful setup should show:
- inbound external mail gets processed
- `chosen_reply_recipient` is logged correctly
- own mail is ignored with reason `self_sender`
- background timer runs every minute
- no repeated self-reply loops
- all unit tests pass (`pytest tests/skills/test_mail_auto_draft_skill.py`)

## References

- `optional-skills/email/mail-auto-draft/config.example.yaml` — configuration template
- `optional-skills/email/mail-auto-draft/process_inbox.py` — main processor (tested)
- `tests/skills/test_mail_auto_draft_skill.py` — unit tests (15+ cases)
- `skills/email/himalaya/references/configuration.md` — official Himalaya setup guide
