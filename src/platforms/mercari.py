import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from .base import PlatformBase
from ..models.listing_data import ListingData
from ..models.sale_data import SaleData
from ..utils.retry import retry_on_failure, RetryConfig
from ..utils.logger import get_logger


class MercariPlatform(PlatformBase):
    """Mercari marketplace platform integration"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger(f"{self.__class__.__name__}")
        
        # Mercari API configuration
        self.api_key = config.get('api_key')
        self.secret = config.get('secret')
        self.access_token = config.get('access_token')
        self.sandbox = config.get('sandbox', True)
        
        # API URLs
        self.base_url = "https://api-sandbox.mercari.com/v1" if self.sandbox else "https://api.mercari.com/v1"
        
        # Condition mapping
        self.condition_mapping = {
            'New': 'new',
            'Like New': 'like_new',
            'Excellent': 'good',
            'Good': 'good',
            'Fair': 'fair',
            'Poor': 'poor'
        }
        
        # Category mapping (simplified)
        self.category_mapping = {
            'Clothing': 'clothing',
            'Shoes': 'shoes',
            'Accessories': 'accessories',
            'Bags': 'bags'
        }
        
        # Fee structure
        self.platform_fee_rate = 0.10  # 10%
        self.payment_fee_rate = 0.029  # 2.9%
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def authenticate(self) -> bool:
        """Authenticate with Mercari API"""
        try:
            headers = self.get_headers()
            headers['Authorization'] = f'Bearer {self.access_token}'
            
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/user/profile",
                headers=headers,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 200
            
            self.logger.log_api_call(
                platform="mercari",
                method="GET",
                url=f"{self.base_url}/user/profile",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                self.authenticated = True
                self.logger.logger.info("Successfully authenticated with Mercari API")
                return True
            else:
                self.logger.logger.error(f"Mercari authentication failed: {response.text}")
                return False
                
        except Exception as e:
            self.logger.log_error(e, {"operation": "authenticate", "platform": "mercari"})
            return False
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def list_item(self, listing_data: ListingData) -> str:
        """Create a new listing on Mercari"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        if not self.validate_listing_data(listing_data):
            raise ValueError("Invalid listing data")
        
        try:
            headers = self.get_headers()
            headers['Authorization'] = f'Bearer {self.access_token}'
            
            payload = {
                'name': listing_data.title,
                'description': listing_data.description,
                'price': int(listing_data.price * 100),  # Convert to cents
                'condition': self.map_condition(listing_data.condition),
                'category': self.map_category(listing_data.category) if listing_data.category else 'other',
                'photos': listing_data.photos[:8],  # Mercari allows up to 8 photos
                'quantity': listing_data.quantity,
                'size': listing_data.size,
                'brand': listing_data.brand
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/items",
                json=payload,
                headers=headers,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 201
            
            self.logger.log_api_call(
                platform="mercari",
                method="POST",
                url=f"{self.base_url}/items",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                response_data = response.json()
                listing_id = response_data['data']['id']
                
                self.logger.log_listing_operation(
                    operation="create",
                    platform="mercari",
                    item_id=listing_data.item_id,
                    listing_id=listing_id,
                    success=True
                )
                
                return listing_id
            else:
                error_msg = f"Failed to create listing: {response.text}"
                self.logger.log_listing_operation(
                    operation="create",
                    platform="mercari",
                    item_id=listing_data.item_id,
                    success=False,
                    error=error_msg
                )
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "list_item",
                "platform": "mercari",
                "item_id": listing_data.item_id
            })
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def update_listing(self, listing_id: str, listing_data: ListingData) -> Dict[str, Any]:
        """Update an existing listing on Mercari"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            headers['Authorization'] = f'Bearer {self.access_token}'
            
            payload = {
                'name': listing_data.title,
                'description': listing_data.description,
                'price': int(listing_data.price * 100),  # Convert to cents
                'condition': self.map_condition(listing_data.condition),
                'quantity': listing_data.quantity
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            start_time = time.time()
            response = requests.put(
                f"{self.base_url}/items/{listing_id}",
                json=payload,
                headers=headers,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 200
            
            self.logger.log_api_call(
                platform="mercari",
                method="PUT",
                url=f"{self.base_url}/items/{listing_id}",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                self.logger.log_listing_operation(
                    operation="update",
                    platform="mercari",
                    item_id=listing_data.item_id,
                    listing_id=listing_id,
                    success=True
                )
                
                return {
                    "success": True,
                    "listing_id": listing_id,
                    "updated_at": datetime.now().isoformat()
                }
            else:
                error_msg = f"Failed to update listing: {response.text}"
                self.logger.log_listing_operation(
                    operation="update",
                    platform="mercari",
                    item_id=listing_data.item_id,
                    listing_id=listing_id,
                    success=False,
                    error=error_msg
                )
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "update_listing",
                "platform": "mercari",
                "listing_id": listing_id
            })
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing from Mercari"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            headers['Authorization'] = f'Bearer {self.access_token}'
            
            start_time = time.time()
            response = requests.delete(
                f"{self.base_url}/items/{listing_id}",
                headers=headers,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 204
            
            self.logger.log_api_call(
                platform="mercari",
                method="DELETE",
                url=f"{self.base_url}/items/{listing_id}",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            self.logger.log_listing_operation(
                operation="delete",
                platform="mercari",
                item_id="",
                listing_id=listing_id,
                success=success,
                error=response.text if not success else None
            )
            
            return success
            
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "delete_listing",
                "platform": "mercari",
                "listing_id": listing_id
            })
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def fetch_listings(self, filters: Dict[str, Any] = None) -> List[ListingData]:
        """Fetch listings from Mercari"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            headers['Authorization'] = f'Bearer {self.access_token}'
            
            params = {}
            if filters:
                params.update(filters)
            
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/items",
                headers=headers,
                params=params,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 200
            
            self.logger.log_api_call(
                platform="mercari",
                method="GET",
                url=f"{self.base_url}/items",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                response_data = response.json()
                listings = []
                
                for item_data in response_data.get('data', []):
                    listing = ListingData(
                        item_id=item_data.get('id'),
                        platform="mercari",
                        platform_listing_id=item_data.get('id'),
                        title=item_data.get('name', ''),
                        description=item_data.get('description', ''),
                        price=item_data.get('price', 0) / 100,  # Convert from cents
                        quantity=item_data.get('quantity', 1),
                        condition=self._reverse_condition_mapping(item_data.get('condition', '')),
                        size=item_data.get('size'),
                        brand=item_data.get('brand'),
                        category=self._reverse_category_mapping(item_data.get('category', '')),
                        photos=item_data.get('photos', []),
                        url=item_data.get('url'),
                        status=item_data.get('status', 'active'),
                        created_at=self._parse_date(item_data.get('created_at')),
                        updated_at=self._parse_date(item_data.get('updated_at')),
                        extra=item_data
                    )
                    listings.append(listing)
                
                return listings
            else:
                raise Exception(f"Failed to fetch listings: {response.text}")
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "fetch_listings",
                "platform": "mercari"
            })
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def fetch_sales(self, date_range: tuple = None) -> List[SaleData]:
        """Fetch sales data from Mercari"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            headers['Authorization'] = f'Bearer {self.access_token}'
            
            params = {}
            if date_range:
                params['start_date'] = date_range[0].isoformat()
                params['end_date'] = date_range[1].isoformat()
            
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/sales",
                headers=headers,
                params=params,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 200
            
            self.logger.log_api_call(
                platform="mercari",
                method="GET",
                url=f"{self.base_url}/sales",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                response_data = response.json()
                sales = []
                
                for sale_data in response_data.get('data', []):
                    gross_amount = sale_data.get('price', 0) / 100  # Convert from cents
                    fees = self.get_platform_fees(gross_amount)
                    
                    sale = SaleData(
                        sale_id=sale_data.get('id'),
                        listing_id=sale_data.get('item_id'),
                        buyer_info=sale_data.get('buyer', {}),
                        sale_date=self._parse_date(sale_data.get('sold_at')),
                        gross_amount=gross_amount,
                        fees=fees,
                        net_amount=gross_amount - fees,
                        platform="mercari",
                        extra=sale_data
                    )
                    sales.append(sale)
                
                return sales
            else:
                raise Exception(f"Failed to fetch sales: {response.text}")
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "fetch_sales",
                "platform": "mercari"
            })
            raise
    
    def get_platform_fees(self, sale_amount: float) -> float:
        """Calculate Mercari platform fees"""
        platform_fee = sale_amount * self.platform_fee_rate
        payment_fee = sale_amount * self.payment_fee_rate
        return round(platform_fee + payment_fee, 2)
    
    def map_condition(self, internal_condition: str) -> str:
        """Map internal condition to Mercari condition"""
        return self.condition_mapping.get(internal_condition, 'good')
    
    def map_category(self, internal_category: str) -> str:
        """Map internal category to Mercari category"""
        return self.category_mapping.get(internal_category, 'other')
    
    def _reverse_condition_mapping(self, mercari_condition: str) -> str:
        """Reverse map Mercari condition to internal condition"""
        reverse_mapping = {v: k for k, v in self.condition_mapping.items()}
        return reverse_mapping.get(mercari_condition, 'Good')
    
    def _reverse_category_mapping(self, mercari_category: str) -> str:
        """Reverse map Mercari category to internal category"""
        reverse_mapping = {v: k for k, v in self.category_mapping.items()}
        return reverse_mapping.get(mercari_category, 'Other')
    
    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_string:
            return None
        
        try:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except ValueError:
            return None
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for Mercari API requests"""
        headers = super().get_headers()
        headers.update({
            'X-API-Key': self.api_key,
            'Accept': 'application/json'
        })
        return headers