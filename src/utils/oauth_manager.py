import requests
import time
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from .logger import get_logger
from .retry import retry_on_failure, RetryConfig


class OAuthTokenManager:
    """OAuth 2.0 token management with automatic refresh"""
    
    def __init__(self, client_id: str, client_secret: str, 
                 token_endpoint: str, config: Dict[str, Any] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_endpoint = token_endpoint
        self.config = config or {}
        
        self.logger = get_logger(self.__class__.__name__)
        
        # Token storage
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.expires_at: Optional[datetime] = None
        self.token_type: str = "Bearer"
        
        # Token refresh settings
        self.refresh_threshold_seconds = self.config.get('refresh_threshold_seconds', 300)  # 5 minutes
        self.max_refresh_retries = self.config.get('max_refresh_retries', 3)
    
    def initialize_tokens(self, access_token: str, refresh_token: str, 
                         expires_in: Optional[int] = None) -> None:
        """Initialize tokens from stored credentials"""
        self.access_token = access_token
        self.refresh_token = refresh_token
        
        if expires_in:
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        self.logger.logger.info("OAuth tokens initialized")
    
    def get_valid_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        if not self.access_token:
            self.logger.logger.warning("No access token available")
            return None
        
        if self._should_refresh_token():
            try:
                self._refresh_access_token()
            except Exception as e:
                self.logger.log_error(e, {"operation": "token_refresh"})
                return None
        
        return self.access_token
    
    def _should_refresh_token(self) -> bool:
        """Check if token should be refreshed"""
        if not self.expires_at or not self.refresh_token:
            return False
        
        # Refresh if token expires within threshold
        time_until_expiry = (self.expires_at - datetime.now()).total_seconds()
        return time_until_expiry <= self.refresh_threshold_seconds
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def _refresh_access_token(self) -> None:
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        self.logger.logger.info("Refreshing OAuth access token")
        
        start_time = time.time()
        response = requests.post(
            self.token_endpoint,
            headers=headers,
            data=data,
            timeout=30
        )
        duration = time.time() - start_time
        
        success = response.status_code == 200
        
        self.logger.log_api_call(
            platform="oauth",
            method="POST",
            url=self.token_endpoint,
            duration=duration,
            success=success,
            status_code=response.status_code,
            error=response.text if not success else None
        )
        
        if success:
            token_data = response.json()
            
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token', self.refresh_token)
            self.token_type = token_data.get('token_type', 'Bearer')
            
            expires_in = token_data.get('expires_in')
            if expires_in:
                self.expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            self.logger.logger.info("OAuth token refreshed successfully")
        else:
            error_msg = f"Token refresh failed: {response.status_code} - {response.text}"
            self.logger.logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_authorization_header(self) -> Dict[str, str]:
        """Get authorization header for API requests"""
        token = self.get_valid_access_token()
        if not token:
            raise Exception("No valid access token available")
        
        return {'Authorization': f'{self.token_type} {token}'}
    
    def revoke_tokens(self) -> bool:
        """Revoke current tokens"""
        if not self.access_token:
            return True
        
        try:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            data = {
                'token': self.access_token,
                'token_type_hint': 'access_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            # Note: Not all OAuth providers support token revocation
            revoke_endpoint = self.token_endpoint.replace('/token', '/revoke')
            response = requests.post(revoke_endpoint, headers=headers, data=data, timeout=30)
            
            # Clear tokens regardless of revocation success
            self.access_token = None
            self.refresh_token = None
            self.expires_at = None
            
            self.logger.logger.info("OAuth tokens revoked")
            return response.status_code in [200, 204]
            
        except Exception as e:
            self.logger.log_error(e, {"operation": "token_revocation"})
            # Clear tokens even if revocation failed
            self.access_token = None
            self.refresh_token = None
            self.expires_at = None
            return False
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get current token information"""
        return {
            'has_access_token': bool(self.access_token),
            'has_refresh_token': bool(self.refresh_token),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'time_until_expiry': (self.expires_at - datetime.now()).total_seconds() if self.expires_at else None,
            'should_refresh': self._should_refresh_token(),
            'token_type': self.token_type
        }
    
    def is_token_valid(self) -> bool:
        """Check if current token is valid and not expired"""
        if not self.access_token:
            return False
        
        if not self.expires_at:
            return True  # Assume valid if no expiry time
        
        return datetime.now() < self.expires_at


class VintedOAuthManager(OAuthTokenManager):
    """Vinted-specific OAuth 2.0 token manager"""
    
    def __init__(self, client_id: str, client_secret: str, config: Dict[str, Any] = None):
        # Vinted OAuth endpoints
        token_endpoint = "https://www.vinted.com/oauth/token"
        
        super().__init__(client_id, client_secret, token_endpoint, config)
        
        # Vinted-specific settings
        self.scope = config.get('scope', ['read', 'write']) if config else ['read', 'write']
        self.redirect_uri = config.get('redirect_uri', 'http://localhost:8080/callback') if config else 'http://localhost:8080/callback'
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get authorization URL for initial OAuth flow"""
        auth_url = "https://www.vinted.com/oauth/authorize"
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scope)
        }
        
        if state:
            params['state'] = state
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        self.logger.logger.info("Exchanging authorization code for tokens")
        
        start_time = time.time()
        response = requests.post(
            self.token_endpoint,
            headers=headers,
            data=data,
            timeout=30
        )
        duration = time.time() - start_time
        
        success = response.status_code == 200
        
        self.logger.log_api_call(
            platform="vinted_oauth",
            method="POST",
            url=self.token_endpoint,
            duration=duration,
            success=success,
            status_code=response.status_code,
            error=response.text if not success else None
        )
        
        if success:
            token_data = response.json()
            
            # Initialize tokens
            self.initialize_tokens(
                access_token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                expires_in=token_data.get('expires_in')
            )
            
            self.logger.logger.info("Successfully exchanged code for tokens")
            return token_data
        else:
            error_msg = f"Token exchange failed: {response.status_code} - {response.text}"
            self.logger.logger.error(error_msg)
            raise Exception(error_msg)
    
    def validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """Validate Vinted webhook signature"""
        import hmac
        import hashlib
        
        if not self.client_secret:
            return False
        
        expected_signature = hmac.new(
            self.client_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)