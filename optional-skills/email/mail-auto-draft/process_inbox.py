#!/usr/bin/env python3
"""
Mail Auto-Draft Processor
Processes inbound email via Himalaya, classifies requests, and drafts/sends replies.
Untrusted input handling: All inbound email content treated as untrusted by default.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import yaml


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> Dict:
    """Load and validate configuration."""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in {config_path}: {e}")
        sys.exit(1)
    
    # Validate required fields
    required = ['own_addresses', 'require_unseen', 'require_whitelist']
    for field in required:
        if field not in config:
            logger.error(f"Missing required config field: {field}")
            sys.exit(1)
    
    return config


def select_reply_recipient(headers: Dict[str, str]) -> Optional[str]:
    """
    Select reply recipient with preference: Reply-To → From.
    Treat header values as untrusted: sanitize and validate.
    """
    # Prefer Reply-To over From
    reply_to = headers.get('Reply-To', '').strip()
    if reply_to and _is_valid_email(reply_to):
        return reply_to
    
    from_addr = headers.get('From', '').strip()
    if from_addr and _is_valid_email(from_addr):
        return from_addr
    
    logger.warning(f"No valid reply recipient found in headers")
    return None


def _is_valid_email(email: str) -> bool:
    """Basic email validation (untrusted input)."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_self_sender(sender: str, own_addresses: set) -> bool:
    """Check if email is from self (self-reply protection)."""
    sender_clean = sender.strip().lower()
    return any(addr.lower() == sender_clean for addr in own_addresses)


def classify_inbound_request(subject: str, body: str) -> str:
    """
    Classify inbound request as safe/uncertain.
    Treat inbound content as untrusted: do not execute or eval.
    """
    subject_lower = subject.lower()
    body_lower = body.lower()
    
    # Simple keyword-based classification (untrusted input safe)
    info_keywords = ['what', 'how', 'when', 'where', 'info', 'information', 'explain']
    appointment_keywords = ['meeting', 'appointment', 'schedule', 'time', 'call', 'zoom']
    ack_keywords = ['thank', 'thanks', 'acknowledge', 'received', 'got it', 'done']
    
    if any(kw in subject_lower for kw in info_keywords):
        return 'info_request'
    elif any(kw in subject_lower for kw in appointment_keywords):
        return 'appointment_request'
    elif any(kw in subject_lower or body_lower for kw in ack_keywords):
        return 'acknowledgment'
    else:
        return 'uncertain'


def get_inbound_mail(limit: int = 5) -> List[Dict]:
    """Fetch new inbound mail via Himalaya CLI."""
    try:
        result = subprocess.run(
            ['himalaya', 'list', 'INBOX', '--limit', str(limit), '--json'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            logger.error(f"Himalaya list failed: {result.stderr}")
            return []
        
        messages = json.loads(result.stdout)
        return messages if isinstance(messages, list) else []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Failed to fetch inbound mail: {e}")
        return []


def read_message_headers(msg_id: str) -> Optional[Dict[str, str]]:
    """Read message headers via Himalaya (untrusted content)."""
    try:
        result = subprocess.run(
            ['himalaya', 'read', msg_id, '--headers'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            logger.warning(f"Failed to read headers for {msg_id}")
            return None
        
        # Parse basic headers (untrusted: sanitize)
        headers = {}
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                headers[key.strip()] = val.strip()
        return headers
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Failed to read message headers: {e}")
        return None


def read_message_body(msg_id: str) -> Optional[str]:
    """Read message body via Himalaya (untrusted content)."""
    try:
        result = subprocess.run(
            ['himalaya', 'read', msg_id],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            logger.warning(f"Failed to read body for {msg_id}")
            return None
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Failed to read message body: {e}")
        return None


def generate_reply_draft(recipient: str, category: str, subject: str) -> Dict[str, str]:
    """Generate reply draft template (untrusted input not included in draft)."""
    templates = {
        'info_request': {
            'subject': f"Re: {subject}",
            'body': "Thank you for your inquiry. I'll get back to you shortly with more information."
        },
        'appointment_request': {
            'subject': f"Re: {subject}",
            'body': "Thank you for reaching out. I'll coordinate a time that works for both of us."
        },
        'acknowledgment': {
            'subject': f"Re: {subject}",
            'body': "Thank you for the update. I appreciate you letting me know."
        },
        'uncertain': {
            'subject': f"Re: {subject}",
            'body': "[DRAFT] This reply requires manual review before sending."
        }
    }
    
    template = templates.get(category, templates['uncertain'])
    return {
        'to': recipient,
        'subject': template['subject'],
        'body': template['body']
    }


def send_reply(draft: Dict[str, str], mode: str = 'draft') -> Tuple[bool, str]:
    """Send or draft reply via Himalaya."""
    to_addr = draft.get('to', '').strip()
    if not to_addr or not _is_valid_email(to_addr):
        return False, "Invalid recipient address"
    
    if mode == 'draft':
        logger.info(f"[DRAFT] Reply to {to_addr}: {draft['subject']}")
        return True, "Draft created (not sent)"
    elif mode == 'auto':
        try:
            result = subprocess.run(
                ['himalaya', 'send', '--to', to_addr, '--subject', draft['subject']],
                input=draft['body'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"[SENT] Reply to {to_addr}: {draft['subject']}")
                return True, "Reply sent"
            else:
                logger.error(f"Send failed: {result.stderr}")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Send timeout"
    else:
        return False, f"Unknown mode: {mode}"


def log_action(msg_id: str, action: str, category: str, recipient: str, config: Dict):
    """Log mail action to JSONL file."""
    log_dir = Path(config.get('log_dir', 'logs'))
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'mail_actions.jsonl'
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'message_id': msg_id,
        'action': action,
        'category': category,
        'chosen_reply_recipient': recipient,
    }
    
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except IOError as e:
        logger.error(f"Failed to log action: {e}")


def process_inbox(mode: str = 'draft', limit: int = 5, config: Optional[Dict] = None):
    """Main processor: fetch, classify, and reply to inbound mail."""
    if config is None:
        config = load_config()
    
    own_addresses = set(config.get('own_addresses', []))
    require_unseen = config.get('require_unseen', True)
    require_whitelist = config.get('require_whitelist', True)
    whitelist_categories = set(config.get('whitelist_categories', ['info_request', 'acknowledgment']))
    forbid_categories = set(config.get('forbid_sensitive_categories', ['sensibel', 'individuell', 'unklar']))
    
    messages = get_inbound_mail(limit)
    logger.info(f"Processing {len(messages)} messages in {mode} mode")
    
    for msg in messages:
        msg_id = msg.get('id')
        if not msg_id:
            continue
        
        sender = msg.get('from', '').strip()
        
        # Self-reply protection
        if is_self_sender(sender, own_addresses):
            logger.info(f"[{msg_id}] Ignoring self-sender: {sender}")
            continue
        
        # Read full message
        headers = read_message_headers(msg_id)
        body = read_message_body(msg_id)
        if not headers or not body:
            logger.warning(f"[{msg_id}] Could not read full message")
            continue
        
        subject = headers.get('Subject', '(no subject)').strip()
        
        # Classify (untrusted input)
        category = classify_inbound_request(subject, body)
        
        # Whitelist check
        if require_whitelist and category not in whitelist_categories:
            logger.info(f"[{msg_id}] Not in whitelist: {category}")
            log_action(msg_id, 'skipped_not_whitelisted', category, '', config)
            continue
        
        # Forbidden category check
        if category in forbid_categories:
            logger.info(f"[{msg_id}] Forbidden category: {category}")
            log_action(msg_id, 'blocked_sensitive', category, '', config)
            continue
        
        # Select recipient
        recipient = select_reply_recipient(headers)
        if not recipient:
            logger.warning(f"[{msg_id}] No valid reply recipient")
            log_action(msg_id, 'error_no_recipient', category, '', config)
            continue
        
        # Generate and send reply
        draft = generate_reply_draft(recipient, category, subject)
        success, msg_result = send_reply(draft, mode)
        
        action = 'sent' if mode == 'auto' else 'drafted'
        log_action(msg_id, action, category, recipient, config)
        
        if not success:
            logger.error(f"[{msg_id}] {action} failed: {msg_result}")


def main():
    parser = argparse.ArgumentParser(description='Process inbound mail and auto-draft replies')
    parser.add_argument('--mode', choices=['draft', 'auto'], default='draft',
                        help='Draft mode (no send) or auto mode (send whitelisted only)')
    parser.add_argument('--limit', type=int, default=5,
                        help='Max messages to process')
    parser.add_argument('--config', default='config.yaml',
                        help='Path to config file')
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    process_inbox(mode=args.mode, limit=args.limit, config=config)


if __name__ == '__main__':
    main()
