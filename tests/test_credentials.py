import os
import pytest
from unittest.mock import MagicMock, patch
from antigravity_manager.credentials import resolve_credentials

@pytest.fixture(autouse=True)
def clear_env():
    """Clear environment variables that might interfere with tests."""
    with patch.dict(os.environ, {}, clear=True):
        yield

def test_resolve_credentials_cli():
    args = MagicMock()
    args.access_key = "cli_key"
    args.secret_key = "cli_secret"
    args.bucket_name = "cli_bucket"
    args.endpoint_url = "cli_endpoint"
    
    # Even if env is set, CLI args should win
    with patch.dict(os.environ, {"AGM_B2_KEY_ID": "env_id"}):
        id, key, bucket, endpoint = resolve_credentials(args)
    assert id == "cli_key"
    assert key == "cli_secret"
    assert bucket == "cli_bucket"
    assert endpoint == "cli_endpoint"

def test_resolve_credentials_env():
    args = MagicMock()
    args.access_key = None
    args.secret_key = None
    args.bucket_name = None
    args.endpoint_url = None
    
    with patch.dict(os.environ, {
        "AGM_B2_KEY_ID": "env_id",
        "AGM_B2_APP_KEY": "env_key",
        "AGM_B2_BUCKET": "env_bucket",
        "AGM_B2_ENDPOINT": "env_endpoint"
    }):
        id, key, bucket, endpoint = resolve_credentials(args)
    
    assert id == "env_id"
    assert key == "env_key"
    assert bucket == "env_bucket"
    assert endpoint == "env_endpoint"

def test_resolve_credentials_doppler():
    args = MagicMock()
    args.access_key = None
    args.secret_key = None
    args.bucket_name = None
    args.endpoint_url = None
    
    with patch.dict(os.environ, {"DOPPLER_TOKEN": "fake_token"}):
        mock_secrets = {
            "AGM_B2_KEY_ID": "doppler_id",
            "AGM_B2_APP_KEY": "doppler_key",
            "AGM_B2_BUCKET": "doppler_bucket",
            "AGM_B2_ENDPOINT": "doppler_endpoint"
        }
        
        with patch("antigravity_manager.credentials.fetch_doppler_secrets", return_value=mock_secrets):
            id, key, bucket, endpoint = resolve_credentials(args)
            assert id == "doppler_id"
            assert key == "doppler_key"
            assert bucket == "doppler_bucket"
            assert endpoint == "doppler_endpoint"

def test_resolve_credentials_fail():
    args = MagicMock()
    args.access_key = None
    args.secret_key = None
    args.bucket_name = None
    args.endpoint_url = None
    
    with pytest.raises(SystemExit):
        with patch("antigravity_manager.credentials.get_doppler_token", return_value=None):
            # Ensure no env vars are present
            with patch.dict(os.environ, {}, clear=True):
                resolve_credentials(args)
