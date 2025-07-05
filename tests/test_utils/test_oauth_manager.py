import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.utils.oauth_manager import OAuthTokenManager, VintedOAuthManager


class TestOAuthTokenManager:
    
    def test_init(self):
        """Test OAuthTokenManager initialization"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        assert manager.client_id == "test_client_id"
        assert manager.client_secret == "test_client_secret"
        assert manager.token_endpoint == "https://example.com/oauth/token"
        assert manager.access_token is None
        assert manager.refresh_token is None
        assert manager.expires_at is None
    
    def test_initialize_tokens(self):
        """Test token initialization"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        manager.initialize_tokens(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_in=3600
        )
        
        assert manager.access_token == "test_access_token"
        assert manager.refresh_token == "test_refresh_token"
        assert manager.expires_at is not None
        assert manager.expires_at > datetime.now()
    
    def test_is_token_valid(self):
        """Test token validity check"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        # No token
        assert manager.is_token_valid() is False
        
        # Valid token
        manager.access_token = "test_token"
        manager.expires_at = datetime.now() + timedelta(hours=1)
        assert manager.is_token_valid() is True
        
        # Expired token
        manager.expires_at = datetime.now() - timedelta(hours=1)
        assert manager.is_token_valid() is False
        
        # Token without expiry (assume valid)
        manager.expires_at = None
        assert manager.is_token_valid() is True
    
    def test_should_refresh_token(self):
        """Test token refresh logic"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        # No refresh token
        assert manager._should_refresh_token() is False
        
        # Set up tokens
        manager.refresh_token = "test_refresh_token"
        manager.expires_at = datetime.now() + timedelta(minutes=10)  # 10 minutes left
        
        # Should not refresh (more than 5 minutes left)
        assert manager._should_refresh_token() is False
        
        # Should refresh (less than 5 minutes left)
        manager.expires_at = datetime.now() + timedelta(minutes=2)  # 2 minutes left
        assert manager._should_refresh_token() is True
    
    @patch('src.utils.oauth_manager.requests.post')
    def test_refresh_access_token_success(self, mock_post):
        """Test successful token refresh"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        manager.refresh_token = "test_refresh_token"
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        manager._refresh_access_token()
        
        assert manager.access_token == "new_access_token"
        assert manager.refresh_token == "new_refresh_token"
        assert manager.token_type == "Bearer"
        assert manager.expires_at is not None
    
    @patch('src.utils.oauth_manager.requests.post')
    def test_refresh_access_token_failure(self, mock_post):
        """Test failed token refresh"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        manager.refresh_token = "test_refresh_token"
        
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            manager._refresh_access_token()
        
        assert "Token refresh failed" in str(exc_info.value)
    
    def test_get_valid_access_token(self):
        """Test getting valid access token"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        # No token
        token = manager.get_valid_access_token()
        assert token is None
        
        # Valid token
        manager.access_token = "test_token"
        manager.expires_at = datetime.now() + timedelta(hours=1)
        token = manager.get_valid_access_token()
        assert token == "test_token"
    
    def test_get_authorization_header(self):
        """Test getting authorization header"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        manager.access_token = "test_token"
        manager.expires_at = datetime.now() + timedelta(hours=1)
        
        header = manager.get_authorization_header()
        assert header == {'Authorization': 'Bearer test_token'}
    
    def test_get_authorization_header_no_token(self):
        """Test getting authorization header without token"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        with pytest.raises(Exception) as exc_info:
            manager.get_authorization_header()
        
        assert "No valid access token available" in str(exc_info.value)
    
    def test_get_token_info(self):
        """Test getting token information"""
        manager = OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_endpoint="https://example.com/oauth/token"
        )
        
        manager.access_token = "test_token"
        manager.refresh_token = "test_refresh_token"
        manager.expires_at = datetime.now() + timedelta(hours=1)
        
        info = manager.get_token_info()
        
        assert info['has_access_token'] is True
        assert info['has_refresh_token'] is True
        assert info['expires_at'] is not None
        assert info['time_until_expiry'] > 0
        assert info['should_refresh'] is False
        assert info['token_type'] == "Bearer"


class TestVintedOAuthManager:
    
    def test_init(self):
        """Test VintedOAuthManager initialization"""
        manager = VintedOAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        assert manager.client_id == "test_client_id"
        assert manager.client_secret == "test_client_secret"
        assert manager.token_endpoint == "https://www.vinted.com/oauth/token"
        assert manager.scope == ['read', 'write']
        assert manager.redirect_uri == 'http://localhost:8080/callback'
    
    def test_get_authorization_url(self):
        """Test getting authorization URL"""
        manager = VintedOAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        auth_url = manager.get_authorization_url()
        
        assert "https://www.vinted.com/oauth/authorize" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "response_type=code" in auth_url
        assert "scope=read write" in auth_url or "scope=read+write" in auth_url or "scope=read%20write" in auth_url
    
    def test_get_authorization_url_with_state(self):
        """Test getting authorization URL with state"""
        manager = VintedOAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        auth_url = manager.get_authorization_url(state="test_state")
        
        assert "state=test_state" in auth_url
    
    @patch('src.utils.oauth_manager.requests.post')
    def test_exchange_code_for_tokens_success(self, mock_post):
        """Test successful code exchange"""
        manager = VintedOAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'access_token_123',
            'refresh_token': 'refresh_token_123',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        token_data = manager.exchange_code_for_tokens("authorization_code_123")
        
        assert token_data['access_token'] == 'access_token_123'
        assert manager.access_token == 'access_token_123'
        assert manager.refresh_token == 'refresh_token_123'
    
    @patch('src.utils.oauth_manager.requests.post')
    def test_exchange_code_for_tokens_failure(self, mock_post):
        """Test failed code exchange"""
        manager = VintedOAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid authorization code"
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            manager.exchange_code_for_tokens("invalid_code")
        
        assert "Token exchange failed" in str(exc_info.value)
    
    def test_validate_webhook_signature(self):
        """Test webhook signature validation"""
        manager = VintedOAuthManager(
            client_id="test_client_id",
            client_secret="test_secret"
        )
        
        payload = "test_payload"
        # Calculate the actual expected signature for the payload and secret
        import hmac
        import hashlib
        expected_signature = hmac.new(
            "test_secret".encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Test with correct signature
        is_valid = manager.validate_webhook_signature(payload, expected_signature)
        assert is_valid is True
        
        # Test with incorrect signature
        is_valid = manager.validate_webhook_signature(payload, "invalid_signature")
        assert is_valid is False
    
    def test_validate_webhook_signature_no_secret(self):
        """Test webhook signature validation without secret"""
        manager = VintedOAuthManager(
            client_id="test_client_id",
            client_secret=None
        )
        
        is_valid = manager.validate_webhook_signature("payload", "signature")
        assert is_valid is False