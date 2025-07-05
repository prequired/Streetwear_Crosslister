from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from ..models.listing_data import ListingData
from ..models.sale_data import SaleData


class PlatformBase(ABC):
    """Abstract base class for all marketplace platform integrations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.authenticated = False
        self.rate_limiter = None
        self.retry_config = config.get('retry_config', {
            'max_retries': 3,
            'backoff_factor': 2,
            'retry_on_status': [429, 500, 502, 503, 504]
        })
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform API"""
        pass
    
    @abstractmethod
    def list_item(self, listing_data: ListingData) -> str:
        """Create a new listing on the platform"""
        pass
    
    @abstractmethod
    def update_listing(self, listing_id: str, listing_data: ListingData) -> Dict[str, Any]:
        """Update an existing listing"""
        pass
    
    @abstractmethod
    def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing from the platform"""
        pass
    
    @abstractmethod
    def fetch_listings(self, filters: Dict[str, Any] = None) -> List[ListingData]:
        """Fetch listings from the platform"""
        pass
    
    @abstractmethod
    def fetch_sales(self, date_range: tuple = None) -> List[SaleData]:
        """Fetch sales data from the platform"""
        pass
    
    @abstractmethod
    def get_platform_fees(self, sale_amount: float) -> float:
        """Calculate platform fees for a sale amount"""
        pass
    
    @abstractmethod
    def map_condition(self, internal_condition: str) -> str:
        """Map internal condition to platform-specific condition"""
        pass
    
    @abstractmethod
    def map_category(self, internal_category: str) -> str:
        """Map internal category to platform-specific category"""
        pass
    
    def validate_listing_data(self, listing_data: ListingData) -> bool:
        """Validate listing data before platform operations"""
        if not listing_data.validate():
            return False
        
        # Platform-specific validation can be implemented in subclasses
        return True
    
    def format_price(self, price: float) -> Any:
        """Format price for platform API (some platforms use cents)"""
        return price
    
    def handle_api_error(self, response, operation: str) -> None:
        """Handle API errors with appropriate logging and exceptions"""
        error_msg = f"API error in {operation}: {response.status_code}"
        if hasattr(response, 'text'):
            error_msg += f" - {response.text}"
        
        self.logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_headers(self) -> Dict[str, str]:
        """Get common headers for API requests"""
        return {
            'User-Agent': 'Streetwear-Inventory-CLI/1.0.0',
            'Content-Type': 'application/json'
        }
    
    def health_check(self) -> bool:
        """Perform basic health check"""
        try:
            return self.authenticate()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False