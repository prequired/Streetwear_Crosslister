import requests
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import base64
import io

from .base import PlatformBase
from ..models.listing_data import ListingData
from ..models.sale_data import SaleData
from ..utils.retry import retry_on_failure, RetryConfig
from ..utils.logger import get_logger
from ..utils.oauth_manager import VintedOAuthManager


class VintedPlatform(PlatformBase):
    """Vinted marketplace platform integration"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger(f"{self.__class__.__name__}")
        
        # Vinted API configuration
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.access_token = config.get('access_token')
        self.refresh_token = config.get('refresh_token')
        
        # Initialize OAuth manager
        self.oauth_manager = VintedOAuthManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            config=config.get('oauth_config', {})
        )
        
        # Initialize with existing tokens if available
        if self.access_token and self.refresh_token:
            self.oauth_manager.initialize_tokens(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                expires_in=config.get('expires_in')
            )
        
        # API URLs
        self.base_url = "https://api.vinted.com/v1"
        
        # Condition mapping (Vinted has specific conditions)
        self.condition_mapping = {
            'New': 'brand_new_with_tag',
            'Like New': 'brand_new_without_tag',
            'Excellent': 'very_good',
            'Good': 'good',
            'Fair': 'satisfactory',
            'Poor': 'poor'
        }
        
        # Size mapping (Vinted has detailed size system)
        self.size_mapping = {
            'XS': 'XS',
            'S': 'S',
            'M': 'M',
            'L': 'L',
            'XL': 'XL',
            'XXL': 'XXL'
        }
        
        # Category mapping (Vinted has complex category hierarchy)
        self.category_mapping = {
            'Clothing': 'clothing',
            'Shoes': 'shoes',
            'Accessories': 'accessories',
            'Bags': 'bags'
        }
        
        # Brand mapping for popular streetwear brands
        self.brand_mapping = {
            'Supreme': 'Supreme',
            'Off-White': 'Off-White',
            'Nike': 'Nike',
            'Adidas': 'Adidas',
            'Stone Island': 'Stone Island',
            'A Bathing Ape': 'A Bathing Ape'
        }
        
        # Vinted fee structure (varies by country)
        self.buyer_protection_fee_rate = 0.03  # 3% buyer protection
        self.platform_fee_rate = 0.05  # 5% platform fee
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def authenticate(self) -> bool:
        """Authenticate with Vinted API using OAuth"""
        try:
            if not self.oauth_manager.is_token_valid():
                self.logger.logger.warning("No valid OAuth token available")
                return False
            
            # Test authentication with user profile endpoint
            headers = self.get_headers()
            headers.update(self.oauth_manager.get_authorization_header())
            
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/user/profile",
                headers=headers,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 200
            
            self.logger.log_api_call(
                platform="vinted",
                method="GET",
                url=f"{self.base_url}/user/profile",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                self.authenticated = True
                user_data = response.json()
                self.logger.logger.info(f"Successfully authenticated with Vinted API as user {user_data.get('user', {}).get('login', 'unknown')}")
                return True
            else:
                self.logger.logger.error(f"Vinted authentication failed: {response.text}")
                return False
                
        except Exception as e:
            self.logger.log_error(e, {"operation": "authenticate", "platform": "vinted"})
            return False
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def list_item(self, listing_data: ListingData) -> str:
        """Create a new listing on Vinted"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        if not self.validate_listing_data(listing_data):
            raise ValueError("Invalid listing data")
        
        try:
            headers = self.get_headers()
            headers.update(self.oauth_manager.get_authorization_header())
            
            # Upload photos first
            photo_ids = []
            if listing_data.photos:
                photo_ids = self._upload_photos(listing_data.photos)
            
            # Get category and brand IDs
            category_id = self._get_category_id(listing_data.category)
            brand_id = self._get_brand_id(listing_data.brand)
            size_id = self._get_size_id(listing_data.size, category_id)
            
            payload = {
                'title': listing_data.title,
                'description': listing_data.description,
                'price': listing_data.price,
                'currency': 'USD',
                'status': 'active',
                'item_condition_id': self._get_condition_id(listing_data.condition),
                'category_id': category_id,
                'brand_id': brand_id,
                'size_id': size_id,
                'photo_ids': photo_ids,
                'quantity': listing_data.quantity,
                'is_hidden': False,
                'is_for_swap': False,
                'is_for_sell': True
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/items",
                json=payload,
                headers=headers,
                timeout=60  # Longer timeout for item creation
            )
            duration = time.time() - start_time
            
            success = response.status_code == 201
            
            self.logger.log_api_call(
                platform="vinted",
                method="POST",
                url=f"{self.base_url}/items",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                response_data = response.json()
                listing_id = str(response_data['item']['id'])
                
                self.logger.log_listing_operation(
                    operation="create",
                    platform="vinted",
                    item_id=listing_data.item_id,
                    listing_id=listing_id,
                    success=True
                )
                
                return listing_id
            else:
                error_msg = f"Failed to create Vinted listing: {response.text}"
                self.logger.log_listing_operation(
                    operation="create",
                    platform="vinted",
                    item_id=listing_data.item_id,
                    success=False,
                    error=error_msg
                )
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "list_item",
                "platform": "vinted",
                "item_id": listing_data.item_id
            })
            raise
    
    def _upload_photos(self, photo_urls: List[str]) -> List[int]:
        """Upload photos to Vinted and return photo IDs"""
        photo_ids = []
        
        for i, photo_url in enumerate(photo_urls[:8]):  # Vinted allows up to 8 photos
            try:
                photo_id = self._upload_single_photo(photo_url)
                if photo_id:
                    photo_ids.append(photo_id)
            except Exception as e:
                self.logger.log_error(e, {
                    "operation": "upload_photo",
                    "photo_url": photo_url,
                    "photo_index": i
                })
                continue
        
        return photo_ids
    
    @retry_on_failure(RetryConfig(max_retries=2, backoff_factor=1.5))
    def _upload_single_photo(self, photo_url: str) -> Optional[int]:
        """Upload a single photo to Vinted"""
        try:
            # Download photo
            photo_response = requests.get(photo_url, timeout=30)
            if photo_response.status_code != 200:
                raise Exception(f"Failed to download photo from {photo_url}")
            
            photo_data = photo_response.content
            
            # Prepare upload
            headers = self.get_headers()
            headers.update(self.oauth_manager.get_authorization_header())
            del headers['Content-Type']  # Let requests set it for multipart
            
            files = {
                'photo': ('image.jpg', photo_data, 'image/jpeg')
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/photos",
                files=files,
                headers=headers,
                timeout=60
            )
            duration = time.time() - start_time
            
            success = response.status_code == 201
            
            self.logger.log_api_call(
                platform="vinted",
                method="POST",
                url=f"{self.base_url}/photos",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                response_data = response.json()
                return response_data['photo']['id']
            else:
                raise Exception(f"Photo upload failed: {response.text}")
                
        except Exception as e:
            self.logger.log_error(e, {"operation": "upload_single_photo", "photo_url": photo_url})
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def update_listing(self, listing_id: str, listing_data: ListingData) -> Dict[str, Any]:
        """Update an existing listing on Vinted"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            headers.update(self.oauth_manager.get_authorization_header())
            
            payload = {
                'title': listing_data.title,
                'description': listing_data.description,
                'price': listing_data.price,
                'status': 'active'
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
                platform="vinted",
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
                    platform="vinted",
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
                error_msg = f"Failed to update Vinted listing: {response.text}"
                self.logger.log_listing_operation(
                    operation="update",
                    platform="vinted",
                    item_id=listing_data.item_id,
                    listing_id=listing_id,
                    success=False,
                    error=error_msg
                )
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "update_listing",
                "platform": "vinted",
                "listing_id": listing_id
            })
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing from Vinted"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            headers.update(self.oauth_manager.get_authorization_header())
            
            start_time = time.time()
            response = requests.delete(
                f"{self.base_url}/items/{listing_id}",
                headers=headers,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code in [200, 204]
            
            self.logger.log_api_call(
                platform="vinted",
                method="DELETE",
                url=f"{self.base_url}/items/{listing_id}",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            self.logger.log_listing_operation(
                operation="delete",
                platform="vinted",
                item_id="",
                listing_id=listing_id,
                success=success,
                error=response.text if not success else None
            )
            
            return success
            
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "delete_listing",
                "platform": "vinted",
                "listing_id": listing_id
            })
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def fetch_listings(self, filters: Dict[str, Any] = None) -> List[ListingData]:
        """Fetch listings from Vinted"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            headers.update(self.oauth_manager.get_authorization_header())
            
            params = {'per_page': 100}
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
                platform="vinted",
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
                
                for item_data in response_data.get('items', []):
                    listing = ListingData(
                        item_id=str(item_data.get('id')),
                        platform="vinted",
                        platform_listing_id=str(item_data.get('id')),
                        title=item_data.get('title', ''),
                        description=item_data.get('description', ''),
                        price=float(item_data.get('price', 0)),
                        quantity=1,  # Vinted typically has quantity 1
                        condition=self._reverse_condition_mapping(item_data.get('status', '')),
                        size=self._get_size_title(item_data.get('size_title', '')),
                        brand=self._get_brand_title(item_data.get('brand_title', '')),
                        category=self._reverse_category_mapping(item_data.get('category', '')),
                        photos=[photo.get('url', '') for photo in item_data.get('photos', [])],
                        url=item_data.get('url'),
                        status='active' if item_data.get('can_be_sold', False) else 'inactive',
                        created_at=self._parse_date(item_data.get('created_at_ts')),
                        updated_at=self._parse_date(item_data.get('updated_at_ts')),
                        extra=item_data
                    )
                    listings.append(listing)
                
                return listings
            else:
                raise Exception(f"Failed to fetch Vinted listings: {response.text}")
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "fetch_listings",
                "platform": "vinted"
            })
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def fetch_sales(self, date_range: tuple = None) -> List[SaleData]:
        """Fetch sales data from Vinted"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            headers.update(self.oauth_manager.get_authorization_header())
            
            params = {'per_page': 100}
            if date_range:
                params['created_at_from'] = date_range[0].isoformat()
                params['created_at_to'] = date_range[1].isoformat()
            
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/transactions",
                headers=headers,
                params=params,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 200
            
            self.logger.log_api_call(
                platform="vinted",
                method="GET",
                url=f"{self.base_url}/transactions",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                response_data = response.json()
                sales = []
                
                for transaction_data in response_data.get('transactions', []):
                    if transaction_data.get('status') != 'sold':
                        continue
                    
                    total_item_price = float(transaction_data.get('total_item_price', 0))
                    fees = self.get_platform_fees(total_item_price)
                    
                    sale = SaleData(
                        sale_id=str(transaction_data.get('id')),
                        listing_id=str(transaction_data.get('item_id', '')),
                        buyer_info=transaction_data.get('buyer', {}),
                        sale_date=self._parse_date(transaction_data.get('created_at')),
                        gross_amount=total_item_price,
                        fees=fees,
                        net_amount=total_item_price - fees,
                        platform="vinted",
                        extra=transaction_data
                    )
                    sales.append(sale)
                
                return sales
            else:
                raise Exception(f"Failed to fetch Vinted sales: {response.text}")
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "fetch_sales",
                "platform": "vinted"
            })
            raise
    
    def get_platform_fees(self, sale_amount: float) -> float:
        """Calculate Vinted platform fees"""
        buyer_protection_fee = sale_amount * self.buyer_protection_fee_rate
        platform_fee = sale_amount * self.platform_fee_rate
        return round(buyer_protection_fee + platform_fee, 2)
    
    def map_condition(self, internal_condition: str) -> str:
        """Map internal condition to Vinted condition"""
        return self.condition_mapping.get(internal_condition, 'good')
    
    def map_category(self, internal_category: str) -> str:
        """Map internal category to Vinted category"""
        return self.category_mapping.get(internal_category, 'clothing')
    
    def _get_category_id(self, category_name: str) -> Optional[int]:
        """Get Vinted category ID (simplified)"""
        # In a real implementation, you'd fetch categories from Vinted API
        category_ids = {
            'clothing': 1,
            'shoes': 2,
            'accessories': 3,
            'bags': 4
        }
        mapped_category = self.map_category(category_name)
        return category_ids.get(mapped_category)
    
    def _get_brand_id(self, brand_name: str) -> Optional[int]:
        """Get Vinted brand ID (simplified)"""
        # In a real implementation, you'd search brands via Vinted API
        if not brand_name:
            return None
        
        # Mock brand IDs for popular streetwear brands
        brand_ids = {
            'Supreme': 1001,
            'Off-White': 1002,
            'Nike': 1003,
            'Adidas': 1004,
            'Stone Island': 1005,
            'A Bathing Ape': 1006
        }
        return brand_ids.get(brand_name)
    
    def _get_size_id(self, size_name: str, category_id: int) -> Optional[int]:
        """Get Vinted size ID based on size and category"""
        if not size_name:
            return None
        
        # Mock size IDs (varies by category in Vinted)
        size_ids = {
            'XS': 101,
            'S': 102,
            'M': 103,
            'L': 104,
            'XL': 105,
            'XXL': 106
        }
        return size_ids.get(size_name)
    
    def _get_condition_id(self, condition_name: str) -> int:
        """Get Vinted condition ID"""
        condition_ids = {
            'brand_new_with_tag': 1,
            'brand_new_without_tag': 2,
            'very_good': 3,
            'good': 4,
            'satisfactory': 5,
            'poor': 6
        }
        mapped_condition = self.map_condition(condition_name)
        return condition_ids.get(mapped_condition, 4)  # Default to 'good'
    
    def _reverse_condition_mapping(self, vinted_condition: str) -> str:
        """Reverse map Vinted condition to internal condition"""
        reverse_mapping = {v: k for k, v in self.condition_mapping.items()}
        return reverse_mapping.get(vinted_condition, 'Good')
    
    def _reverse_category_mapping(self, vinted_category: str) -> str:
        """Reverse map Vinted category to internal category"""
        reverse_mapping = {v: k for k, v in self.category_mapping.items()}
        return reverse_mapping.get(vinted_category, 'Clothing')
    
    def _get_size_title(self, size_title: str) -> str:
        """Extract size from Vinted size title"""
        return size_title or ""
    
    def _get_brand_title(self, brand_title: str) -> str:
        """Extract brand from Vinted brand title"""
        return brand_title or ""
    
    def _parse_date(self, date_input) -> Optional[datetime]:
        """Parse date from timestamp or string"""
        if not date_input:
            return None
        
        try:
            if isinstance(date_input, (int, float)):
                return datetime.fromtimestamp(date_input)
            elif isinstance(date_input, str):
                return datetime.fromisoformat(date_input.replace('Z', '+00:00'))
            else:
                return None
        except (ValueError, TypeError):
            return None
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for Vinted API requests"""
        headers = super().get_headers()
        headers.update({
            'Accept': 'application/json',
            'Accept-Language': 'en',
        })
        return headers