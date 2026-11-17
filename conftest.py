"""
pytest configuration for mail auto-draft skill tests.

Registers custom pytest marks and provides test fixtures.
"""

import pytest
from pathlib import Path
import tempfile


def pytest_configure(config):
    """Register custom pytest marks."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring real mail account (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )


@pytest.fixture(scope="session")
def mail_account_available(request):
    """Check if a test mail account is configured."""
    import os
    return os.getenv("MAIL_AUTO_DRAFT_TEST_ACCOUNT") is not None


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide a temporary config directory for tests."""
    config_dir = tmp_path / ".config" / "mail-auto-draft"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def temp_bin_dir(tmp_path):
    """Provide a temporary bin directory for tests."""
    bin_dir = tmp_path / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir


@pytest.fixture
def temp_data_dir(tmp_path):
    """Provide a temporary data directory for logs."""
    data_dir = tmp_path / ".local" / "share" / "mail-auto-draft"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def mock_himalaya_env(tmp_path, monkeypatch):
    """Mock Himalaya environment for testing."""
    config_dir = tmp_path / ".config" / "himalaya"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a minimal config file
    config_file = config_dir / "config.toml"
    config_file.write_text("""
[account.test]
backend = "imap"
imap-host = "imap.example.com"
imap-port = 993
imap-security = "imaps"
imap-login = "test@example.com"
smtp-host = "smtp.example.com"
smtp-port = 587
smtp-security = "starttls"
smtp-login = "test@example.com"

[account.test.folder.aliases]
sent = "[Gmail]/Sent Mail"
drafts = "[Gmail]/Drafts"
""")
    
    monkeypatch.setenv("HOME", str(tmp_path))
    return config_dir
