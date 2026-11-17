#!/usr/bin/env python3
"""
Himalaya-based inbound email auto-draft processor.

Monitors a configured mailbox for new inbound messages and automatically
drafts replies for safe categories (information requests, appointment requests,
acknowledgements) while preventing self-reply loops.

Usage:
    process_inbox.py [--config CONFIG_PATH] [--mailbox MAILBOX] [--dry-run]

Environment variables:
    MAIL_AUTO_DRAFT_CONFIG: Path to config file (~/.config/mail-auto-draft/config.yaml)
    MAIL_AUTO_DRAFT_MAILBOX: Mailbox to monitor (default: INBOX)
    MAIL_AUTO_DRAFT_DRY_RUN: If set, create drafts but don't send (default behavior)
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import argparse
import yaml


class MailAutoDraftProcessor:
    """Process inbound emails and create auto-draft replies."""

    # Safe categories that allow auto-send (if enabled in config)
    SAFE_CATEGORIES = {
        "information_request",
        "appointment_request",
        "acknowledgement",
    }

    def __init__(
        self,
        config_path: Optional[str] = None,
        mailbox: str = "INBOX",
        dry_run: bool = True,
    ):
        """Initialize processor with configuration."""
        self.mailbox = mailbox
        self.dry_run = dry_run
        self.logger = self._setup_logging()

        # Load config
        if config_path is None:
            config_path = os.path.expandvars(
                "$HOME/.config/mail-auto-draft/config.yaml"
            )
        self.config = self._load_config(config_path)

        # Extract settings
        self.own_addresses: Set[str] = set(self.config.get("own_addresses", []))
        self.whitelist_senders: Set[str] = set(self.config.get("whitelist_senders", []))
        self.auto_send_enabled: bool = self.config.get("auto_send_enabled", False)
        self.rate_limit_per_hour: int = self.config.get("rate_limit_per_hour", 5)
        self.rate_limit_per_day: int = self.config.get("rate_limit_per_day", 20)

        # Track sent messages for rate limiting
        self.replies_sent_today: List[datetime] = []
        self.replies_sent_this_hour: List[datetime] = []

    def _setup_logging(self) -> logging.Logger:
        """Configure logging."""
        logger = logging.getLogger("mail-auto-draft")
        logger.setLevel(logging.DEBUG)

        # Log to file
        log_dir = Path.home() / ".local" / "share" / "mail-auto-draft"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "processor.log"

        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path).expanduser()
        if not config_file.exists():
            self.logger.error(f"Config file not found: {config_file}")
            return {}

        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Loaded config from {config_file}")
            return config or {}
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    def process(self) -> bool:
        """Process inbox and create auto-draft replies."""
        self.logger.info(f"Starting processor (dry_run={self.dry_run})")

        try:
            # List unread messages
            messages = self._list_messages()
            if not messages:
                self.logger.info("No new messages to process")
                return True

            self.logger.info(f"Found {len(messages)} new messages")

            for msg in messages:
                try:
                    self._process_message(msg)
                except Exception as e:
                    self.logger.error(f"Error processing message {msg.get('id')}: {e}")

            self.logger.info("Processor completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Processor failed: {e}")
            return False

    def _list_messages(self) -> List[Dict]:
        """List unread messages from mailbox."""
        try:
            result = subprocess.run(
                [
                    "himalaya",
                    "message",
                    "list",
                    "--mailbox",
                    self.mailbox,
                    "--query",
                    "flag:unread",
                    "--output",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.logger.error(f"Himalaya list failed: {result.stderr}")
                return []

            # Parse JSON output
            messages = json.loads(result.stdout) if result.stdout else []
            return messages if isinstance(messages, list) else []

        except subprocess.TimeoutExpired:
            self.logger.error("Himalaya list timed out")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Himalaya output: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to list messages: {e}")
            return []

    def _process_message(self, msg: Dict) -> bool:
        """Process a single message and create draft reply."""
        msg_id = msg.get("id")
        sender = msg.get("from", "").lower()

        self.logger.info(f"Processing message {msg_id} from {sender}")

        # Check: skip if from own address
        if self._is_own_address(sender):
            self.logger.info(f"Skipping self-reply from {sender}")
            return False

        # Check: require whitelist for auto-send
        if self.auto_send_enabled and not self._is_whitelisted(sender):
            self.logger.info(f"Sender {sender} not whitelisted; draft-only mode")
            self.auto_send_enabled = False  # Force draft-only for this message

        # Read message headers and body
        headers, body = self._read_message(msg_id)
        if not headers or not body:
            self.logger.error(f"Failed to read message {msg_id}")
            return False

        # Categorize message
        category = self._categorize_message(headers, body)
        self.logger.info(f"Message categorized as: {category}")

        # Check: category allowed?
        if category not in self.SAFE_CATEGORIES:
            self.logger.info(f"Category {category} not in safe list; draft-only")
            self.auto_send_enabled = False

        # Extract recipients (Reply-To aware)
        recipients = self._extract_recipients(headers)
        if not recipients:
            self.logger.warning(f"No recipients for message {msg_id}")
            return False

        # Generate draft reply
        reply_subject = self._generate_reply_subject(headers)
        reply_body = self._generate_reply_body(category, body)

        # Create draft
        draft_id = self._create_draft(recipients, reply_subject, reply_body)
        if not draft_id:
            self.logger.error(f"Failed to create draft for message {msg_id}")
            return False

        self.logger.info(f"Created draft {draft_id} for message {msg_id}")

        # Auto-send if allowed and not dry-run
        if self.auto_send_enabled and not self.dry_run:
            if self._check_rate_limit():
                if self._send_draft(draft_id):
                    self.logger.info(f"Sent draft {draft_id}")
                    self._record_sent_time()
                    self._mark_as_read(msg_id)
                    return True
                else:
                    self.logger.error(f"Failed to send draft {draft_id}")
                    return False
            else:
                self.logger.warning("Rate limit exceeded; keeping as draft")
                return False

        self.logger.info(f"Draft {draft_id} ready for review (dry_run={self.dry_run})")
        return True

    def _is_own_address(self, sender: str) -> bool:
        """Check if sender is one of our own addresses."""
        sender_clean = sender.strip().lower()
        return any(addr.strip().lower() == sender_clean for addr in self.own_addresses)

    def _is_whitelisted(self, sender: str) -> bool:
        """Check if sender is in whitelist."""
        sender_clean = sender.strip().lower()
        if not self.whitelist_senders:
            return False  # Empty whitelist = deny all
        return any(
            addr.strip().lower() == sender_clean for addr in self.whitelist_senders
        )

    def _read_message(self, msg_id: str) -> tuple[Optional[Dict], Optional[str]]:
        """Read message headers and body."""
        try:
            result = subprocess.run(
                [
                    "himalaya",
                    "message",
                    "read",
                    "--mailbox",
                    self.mailbox,
                    "--output",
                    "json",
                    msg_id,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                self.logger.error(f"Himalaya read failed: {result.stderr}")
                return None, None

            msg = json.loads(result.stdout)
            headers = msg.get("headers", {})
            body = msg.get("body", "")
            return headers, body

        except Exception as e:
            self.logger.error(f"Failed to read message {msg_id}: {e}")
            return None, None

    def _categorize_message(self, headers: Dict, body: str) -> str:
        """Categorize message based on subject and content."""
        subject = headers.get("Subject", "").lower()
        body_lower = body.lower()

        # Simple keyword-based categorization
        if any(
            keyword in subject or keyword in body_lower
            for keyword in ["appoint", "meeting", "schedule", "book"]
        ):
            return "appointment_request"
        elif any(
            keyword in subject or keyword in body_lower
            for keyword in ["info", "question", "how", "what", "where"]
        ):
            return "information_request"
        elif any(
            keyword in subject or keyword in body_lower
            for keyword in ["thanks", "thank you", "got it", "acknowledge", "received"]
        ):
            return "acknowledgement"
        else:
            return "unknown"

    def _extract_recipients(self, headers: Dict) -> List[str]:
        """Extract recipients, preferring Reply-To over From."""
        reply_to = headers.get("Reply-To", "").strip()
        if reply_to:
            # Split on comma and clean
            recipients = [addr.strip() for addr in reply_to.split(",")]
            return [r for r in recipients if r]

        from_addr = headers.get("From", "").strip()
        return [from_addr] if from_addr else []

    def _generate_reply_subject(self, headers: Dict) -> str:
        """Generate reply subject (Re: ...)."""
        original_subject = headers.get("Subject", "")
        if original_subject.lower().startswith("re:"):
            return original_subject
        return f"Re: {original_subject}"

    def _generate_reply_body(self, category: str, original_body: str) -> str:
        """Generate reply body based on category."""
        templates = {
            "information_request": (
                "Thank you for your question. I've noted your inquiry and will "
                "get back to you shortly with the information you need.\n\n"
                "Best regards"
            ),
            "appointment_request": (
                "Thank you for reaching out to schedule an appointment. "
                "I've received your request and will confirm availability soon.\n\n"
                "Best regards"
            ),
            "acknowledgement": (
                "Thank you for your message. I've received it and appreciate you "
                "reaching out.\n\n"
                "Best regards"
            ),
        }
        return templates.get(category, "Thank you for your message.\n\nBest regards")

    def _create_draft(
        self, recipients: List[str], subject: str, body: str
    ) -> Optional[str]:
        """Create a draft message."""
        try:
            # Use himalaya to compose draft
            message_content = f"Subject: {subject}\nTo: {', '.join(recipients)}\n\n{body}"

            result = subprocess.run(
                [
                    "himalaya",
                    "message",
                    "write",
                    "--mailbox",
                    self.mailbox,
                    "--output",
                    "json",
                ],
                input=message_content,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                self.logger.error(f"Failed to create draft: {result.stderr}")
                return None

            output = json.loads(result.stdout)
            draft_id = output.get("id")
            return draft_id

        except Exception as e:
            self.logger.error(f"Failed to create draft: {e}")
            return None

    def _check_rate_limit(self) -> bool:
        """Check if rate limits allow sending."""
        now = datetime.now()

        # Clean up old timestamps
        self.replies_sent_today = [
            t for t in self.replies_sent_today if (now - t).days < 1
        ]
        self.replies_sent_this_hour = [
            t for t in self.replies_sent_this_hour if (now - t).seconds < 3600
        ]

        # Check limits
        if len(self.replies_sent_this_hour) >= self.rate_limit_per_hour:
            self.logger.warning(
                f"Hourly rate limit reached ({self.rate_limit_per_hour})"
            )
            return False

        if len(self.replies_sent_today) >= self.rate_limit_per_day:
            self.logger.warning(
                f"Daily rate limit reached ({self.rate_limit_per_day})"
            )
            return False

        return True

    def _record_sent_time(self) -> None:
        """Record that a message was sent."""
        now = datetime.now()
        self.replies_sent_today.append(now)
        self.replies_sent_this_hour.append(now)

    def _send_draft(self, draft_id: str) -> bool:
        """Send a draft message."""
        try:
            result = subprocess.run(
                [
                    "himalaya",
                    "message",
                    "send",
                    "--mailbox",
                    self.mailbox,
                    draft_id,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.logger.error(f"Failed to send draft: {result.stderr}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to send draft: {e}")
            return False

    def _mark_as_read(self, msg_id: str) -> bool:
        """Mark original message as read."""
        try:
            result = subprocess.run(
                [
                    "himalaya",
                    "message",
                    "flag",
                    "--mailbox",
                    self.mailbox,
                    "--set",
                    "seen",
                    msg_id,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Failed to mark message as read: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process inbound emails and create auto-draft replies"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config file (default: ~/.config/mail-auto-draft/config.yaml)",
    )
    parser.add_argument(
        "--mailbox",
        type=str,
        default="INBOX",
        help="Mailbox to monitor (default: INBOX)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Create drafts but don't send (default: True)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually send approved messages (requires explicit opt-in)",
    )

    args = parser.parse_args()

    # Create processor
    processor = MailAutoDraftProcessor(
        config_path=args.config,
        mailbox=args.mailbox,
        dry_run=not args.send,
    )

    # Run
    success = processor.process()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
