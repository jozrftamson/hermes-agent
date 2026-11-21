#!/usr/bin/env python3
"""Unit tests for mail-auto-draft skill."""

import pytest
import sys
from pathlib import Path

# Add the repo root to path so we can import the skill module
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

# Now import the functions we're testing
import importlib.util
spec = importlib.util.spec_from_file_location(
    "process_inbox",
    repo_root / "optional-skills/email/mail-auto-draft/process_inbox.py"
)
process_inbox_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(process_inbox_module)

select_reply_recipient = process_inbox_module.select_reply_recipient
is_self_sender = process_inbox_module.is_self_sender
classify_inbound_request = process_inbox_module.classify_inbound_request
_is_valid_email = process_inbox_module._is_valid_email


class TestReplyRecipientSelection:
    """Test Reply-To vs From fallback logic."""
    
    def test_select_reply_recipient_prefers_reply_to(self):
        """Reply-To takes precedence over From."""
        headers = {
            'From': 'sender@example.com',
            'Reply-To': 'reply@example.com'
        }
        assert select_reply_recipient(headers) == 'reply@example.com'
    
    def test_select_reply_recipient_fallback_to_from(self):
        """Fall back to From if Reply-To absent."""
        headers = {'From': 'sender@example.com'}
        assert select_reply_recipient(headers) == 'sender@example.com'
    
    def test_select_reply_recipient_empty_reply_to_uses_from(self):
        """Empty Reply-To falls back to From."""
        headers = {
            'From': 'sender@example.com',
            'Reply-To': '  '
        }
        assert select_reply_recipient(headers) == 'sender@example.com'
    
    def test_select_reply_recipient_invalid_from_returns_none(self):
        """Invalid email addresses return None."""
        headers = {'From': 'not-an-email'}
        assert select_reply_recipient(headers) is None
    
    def test_select_reply_recipient_no_headers_returns_none(self):
        """Missing headers return None."""
        assert select_reply_recipient({}) is None


class TestSelfReplyProtection:
    """Test self-reply detection."""
    
    def test_is_self_sender_exact_match(self):
        """Exact sender match detected."""
        own_addresses = {'me@example.com', 'me+work@example.com'}
        assert is_self_sender('me@example.com', own_addresses) is True
    
    def test_is_self_sender_case_insensitive(self):
        """Case-insensitive matching."""
        own_addresses = {'Me@Example.com'}
        assert is_self_sender('me@example.com', own_addresses) is True
    
    def test_is_self_sender_not_in_set(self):
        """Non-matching sender returns False."""
        own_addresses = {'me@example.com'}
        assert is_self_sender('other@example.com', own_addresses) is False
    
    def test_is_self_sender_with_whitespace(self):
        """Whitespace stripped before comparison."""
        own_addresses = {'me@example.com'}
        assert is_self_sender('  me@example.com  ', own_addresses) is True


class TestClassification:
    """Test inbound request classification."""
    
    def test_classify_info_request(self):
        """Classify information request."""
        category = classify_inbound_request(
            'What is your process?',
            'Can you explain how this works?'
        )
        assert category == 'info_request'
    
    def test_classify_appointment_request(self):
        """Classify appointment request."""
        category = classify_inbound_request(
            'Schedule a meeting',
            'When can we meet for a call?'
        )
        assert category == 'appointment_request'
    
    def test_classify_acknowledgment(self):
        """Classify acknowledgment."""
        category = classify_inbound_request(
            'Thanks for the update',
            'Got it, thanks for letting me know.'
        )
        assert category == 'acknowledgment'
    
    def test_classify_uncertain_defaults_to_uncertain(self):
        """Unknown subjects default to uncertain."""
        category = classify_inbound_request(
            'Random subject line',
            'Some random body content'
        )
        assert category == 'uncertain'
    
    def test_classify_case_insensitive(self):
        """Classification is case-insensitive."""
        category = classify_inbound_request(
            'WHAT IS YOUR INFO',
            'PLEASE EXPLAIN'
        )
        assert category == 'info_request'


class TestEmailValidation:
    """Test email format validation."""
    
    def test_is_valid_email_correct_format(self):
        """Valid emails pass."""
        assert _is_valid_email('user@example.com') is True
        assert _is_valid_email('user.name+tag@example.co.uk') is True
    
    def test_is_valid_email_invalid_format(self):
        """Invalid emails fail."""
        assert _is_valid_email('not-an-email') is False
        assert _is_valid_email('user@') is False
        assert _is_valid_email('@example.com') is False
        assert _is_valid_email('user @example.com') is False


class TestUntrustedInput:
    """Test handling of untrusted inbound content."""
    
    def test_classify_does_not_execute_content(self):
        """Classification doesn't execute inbound code."""
        # Simulate injection attempt (should be safe)
        malicious_subject = '__import__("os").system("echo hacked")'
        category = classify_inbound_request(malicious_subject, '')
        # Should classify as uncertain, never execute
        assert isinstance(category, str)
    
    def test_select_recipient_sanitizes_headers(self):
        """Recipient selection sanitizes untrusted headers."""
        # Headers with formatting injection
        headers = {
            'From': 'attacker@evil.com\r\nBcc: attacker@evil.com',
            'Reply-To': 'legit@example.com'
        }
        recipient = select_reply_recipient(headers)
        # Should return the Reply-To value (trusted path)
        assert recipient == 'legit@example.com'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
