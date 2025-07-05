import requests
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import PlatformBase
from ..models.listing_data import ListingData
from ..models.sale_data import SaleData
from ..utils.retry import retry_on_failure, RetryConfig
from ..utils.logger import get_logger


class FacebookMarketplacePlatform(PlatformBase):
    """Facebook Marketplace platform integration using Graph API"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger(f"{self.__class__.__name__}")
        
        # Facebook API configuration
        self.app_id = config.get('app_id')
        self.app_secret = config.get('app_secret')
        self.access_token = config.get('access_token')
        self.page_id = config.get('page_id')
        
        # Graph API URLs
        self.graph_version = config.get('graph_version', 'v18.0')
        self.base_url = f"https://graph.facebook.com/{self.graph_version}"
        
        # Condition mapping for Facebook Marketplace
        self.condition_mapping = {
            'New': 'NEW',
            'Like New': 'LIKE_NEW',
            'Excellent': 'GOOD',
            'Good': 'GOOD',
            'Fair': 'FAIR',
            'Poor': 'POOR'
        }
        
        # Category mapping (Facebook has specific category IDs)
        self.category_mapping = {
            'Clothing': 'APPAREL',
            'Shoes': 'SHOES',
            'Accessories': 'ACCESSORIES',
            'Bags': 'BAGS_AND_LUGGAGE'
        }
        
        # Facebook doesn't charge fees for organic marketplace listings
        self.platform_fee_rate = 0.0
        
        # Product catalog ID (required for marketplace listings)
        self.catalog_id = config.get('catalog_id')
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def authenticate(self) -> bool:
        """Authenticate with Facebook Graph API"""
        try:
            # Test authentication with page access
            headers = self.get_headers()
            
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/me",
                headers=headers,
                params={'access_token': self.access_token},
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 200
            
            self.logger.log_api_call(
                platform="facebook_marketplace",
                method="GET",
                url=f"{self.base_url}/me",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                self.authenticated = True
                user_data = response.json()
                self.logger.logger.info(f"Successfully authenticated with Facebook Graph API as {user_data.get('name', 'unknown')}")
                return True
            else:
                self.logger.logger.error(f"Facebook authentication failed: {response.text}")
                return False
                
        except Exception as e:
            self.logger.log_error(e, {"operation": "authenticate", "platform": "facebook_marketplace"})
            return False
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def list_item(self, listing_data: ListingData) -> str:
        """Create a new listing on Facebook Marketplace"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        if not self.validate_listing_data(listing_data):
            raise ValueError("Invalid listing data")
        
        try:
            # Step 1: Create product in catalog
            product_id = self._create_product_in_catalog(listing_data)
            
            # Step 2: Create marketplace listing
            listing_id = self._create_marketplace_listing(product_id, listing_data)
            
            self.logger.log_listing_operation(
                operation="create",
                platform="facebook_marketplace",
                item_id=listing_data.item_id,
                listing_id=listing_id,
                success=True
            )
            
            return listing_id
            
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "list_item",
                "platform": "facebook_marketplace",
                "item_id": listing_data.item_id
            })
            raise
    
    def _create_product_in_catalog(self, listing_data: ListingData) -> str:
        """Create a product in Facebook catalog"""
        if not self.catalog_id:
            raise Exception("Catalog ID not configured for Facebook Marketplace")
        
        headers = self.get_headers()
        
        # Upload photos first
        image_urls = listing_data.photos[:10] if listing_data.photos else []
        
        payload = {
            'name': listing_data.title,
            'description': listing_data.description,
            'price': int(listing_data.price * 100),  # Price in cents
            'currency': 'USD',
            'condition': self.map_condition(listing_data.condition),
            'category': self.map_category(listing_data.category),
            'brand': listing_data.brand or '',
            'size': listing_data.size or '',
            'image_url': image_urls[0] if image_urls else '',
            'additional_image_urls': image_urls[1:] if len(image_urls) > 1 else [],
            'availability': 'in stock',
            'inventory': listing_data.quantity,
            'retailer_id': listing_data.item_id,
            'access_token': self.access_token
        }
        
        # Remove empty values
        payload = {k: v for k, v in payload.items() if v not in [None, '', []]}
        
        start_time = time.time()
        response = requests.post(
            f"{self.base_url}/{self.catalog_id}/products",
            json=payload,
            headers=headers,
            timeout=60
        )
        duration = time.time() - start_time
        
        success = response.status_code == 200
        
        self.logger.log_api_call(
            platform="facebook_marketplace",
            method="POST",
            url=f"{self.base_url}/{self.catalog_id}/products",
            duration=duration,
            success=success,
            status_code=response.status_code,
            error=response.text if not success else None
        )
        
        if success:
            response_data = response.json()
            return response_data['id']
        else:
            error_msg = f"Failed to create Facebook product: {response.text}"
            raise Exception(error_msg)
    
    def _create_marketplace_listing(self, product_id: str, listing_data: ListingData) -> str:
        """Create a marketplace listing from catalog product"""
        headers = self.get_headers()
        
        payload = {
            'product_id': product_id,
            'access_token': self.access_token
        }
        
        start_time = time.time()
        response = requests.post(
            f"{self.base_url}/{self.page_id}/marketplace_listings",
            json=payload,
            headers=headers,
            timeout=30
        )
        duration = time.time() - start_time
        
        success = response.status_code == 200
        
        self.logger.log_api_call(
            platform="facebook_marketplace",
            method="POST",
            url=f"{self.base_url}/{self.page_id}/marketplace_listings",
            duration=duration,
            success=success,
            status_code=response.status_code,
            error=response.text if not success else None
        )
        
        if success:
            response_data = response.json()
            return response_data['id']
        else:
            error_msg = f"Failed to create Facebook marketplace listing: {response.text}"
            raise Exception(error_msg)
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def update_listing(self, listing_id: str, listing_data: ListingData) -> Dict[str, Any]:
        """Update an existing listing on Facebook Marketplace"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            
            # Facebook Marketplace updates are typically done at the product level
            payload = {
                'name': listing_data.title,
                'description': listing_data.description,
                'price': int(listing_data.price * 100),
                'inventory': listing_data.quantity,
                'access_token': self.access_token
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/{listing_id}",
                json=payload,
                headers=headers,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 200
            
            self.logger.log_api_call(
                platform="facebook_marketplace",
                method="POST",
                url=f"{self.base_url}/{listing_id}",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                self.logger.log_listing_operation(
                    operation="update",
                    platform="facebook_marketplace",
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
                error_msg = f"Failed to update Facebook listing: {response.text}"
                self.logger.log_listing_operation(
                    operation="update",
                    platform="facebook_marketplace",
                    item_id=listing_data.item_id,
                    listing_id=listing_id,
                    success=False,
                    error=error_msg
                )
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "update_listing",
                "platform": "facebook_marketplace",
                "listing_id": listing_id
            })
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing from Facebook Marketplace"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            
            start_time = time.time()
            response = requests.delete(
                f"{self.base_url}/{listing_id}",
                headers=headers,
                params={'access_token': self.access_token},
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code in [200, 204]
            
            self.logger.log_api_call(
                platform="facebook_marketplace",
                method="DELETE",
                url=f"{self.base_url}/{listing_id}",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            self.logger.log_listing_operation(
                operation="delete",
                platform="facebook_marketplace",
                item_id="",
                listing_id=listing_id,
                success=success,
                error=response.text if not success else None
            )
            
            return success
            
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "delete_listing",
                "platform": "facebook_marketplace",
                "listing_id": listing_id
            })
            raise
    
    @retry_on_failure(RetryConfig(max_retries=3, backoff_factor=2))
    def fetch_listings(self, filters: Dict[str, Any] = None) -> List[ListingData]:
        """Fetch listings from Facebook Marketplace"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        try:
            headers = self.get_headers()
            
            params = {
                'access_token': self.access_token,
                'fields': 'id,name,description,price,condition,category,brand,image_url,availability,inventory,retailer_id'
            }
            
            if filters:
                params.update(filters)
            
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/{self.catalog_id}/products",
                headers=headers,
                params=params,
                timeout=30
            )
            duration = time.time() - start_time
            
            success = response.status_code == 200
            
            self.logger.log_api_call(
                platform="facebook_marketplace",
                method="GET",
                url=f"{self.base_url}/{self.catalog_id}/products",
                duration=duration,
                success=success,
                status_code=response.status_code,
                error=response.text if not success else None
            )
            
            if success:
                response_data = response.json()
                listings = []
                
                for product_data in response_data.get('data', []):
                    listing = ListingData(
                        item_id=product_data.get('retailer_id', product_data.get('id')),
                        platform="facebook_marketplace",
                        platform_listing_id=product_data.get('id'),
                        title=product_data.get('name', ''),
                        description=product_data.get('description', ''),
                        price=float(product_data.get('price', 0)) / 100,  # Convert from cents
                        quantity=product_data.get('inventory', 1),
                        condition=self._reverse_condition_mapping(product_data.get('condition', '')),
                        brand=product_data.get('brand', ''),
                        category=self._reverse_category_mapping(product_data.get('category', '')),
                        photos=[product_data.get('image_url', '')] if product_data.get('image_url') else [],
                        status='active' if product_data.get('availability') == 'in stock' else 'inactive',
                        extra=product_data
                    )
                    listings.append(listing)
                
                return listings
            else:
                raise Exception(f"Failed to fetch Facebook listings: {response.text}")
                
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "fetch_listings",
                "platform": "facebook_marketplace"
            })
            raise
    
    def fetch_sales(self, date_range: tuple = None) -> List[SaleData]:
        """Fetch sales data from Facebook Marketplace (limited data available)"""
        if not self.authenticated:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        # Note: Facebook Marketplace doesn't provide comprehensive sales data via API
        # This would typically require webhook integration for real-time updates
        
        self.logger.logger.warning("Facebook Marketplace sales data is limited via API. Consider webhook integration for real-time updates.")
        
        # Return empty list as Facebook doesn't provide detailed sales data
        return []
    
    def get_platform_fees(self, sale_amount: float) -> float:
        """Calculate Facebook Marketplace platform fees (typically none for organic listings)"""
        return 0.0  # Facebook doesn't charge fees for organic marketplace listings
    
    def map_condition(self, internal_condition: str) -> str:
        """Map internal condition to Facebook condition"""
        return self.condition_mapping.get(internal_condition, 'GOOD')
    
    def map_category(self, internal_category: str) -> str:
        """Map internal category to Facebook category"""
        return self.category_mapping.get(internal_category, 'APPAREL')
    
    def _reverse_condition_mapping(self, facebook_condition: str) -> str:
        """Reverse map Facebook condition to internal condition"""
        reverse_mapping = {v: k for k, v in self.condition_mapping.items()}
        return reverse_mapping.get(facebook_condition, 'Good')
    
    def _reverse_category_mapping(self, facebook_category: str) -> str:
        """Reverse map Facebook category to internal category"""
        reverse_mapping = {v: k for k, v in self.category_mapping.items()}
        return reverse_mapping.get(facebook_category, 'Clothing')
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for Facebook Graph API requests"""
        headers = super().get_headers()
        headers.update({
            'Accept': 'application/json',
        })
        return headers
    
    def health_check(self) -> bool:
        """Perform health check specific to Facebook Marketplace"""
        try:
            # Check both Graph API access and catalog access
            api_check = self.authenticate()
            
            if not api_check:
                return False
            
            # Check catalog access
            headers = self.get_headers()
            response = requests.get(
                f"{self.base_url}/{self.catalog_id}",
                headers=headers,
                params={'access_token': self.access_token},
                timeout=30
            )
            
            catalog_check = response.status_code == 200
            
            return api_check and catalog_check
            
        except Exception as e:
            self.logger.log_error(e, {"operation": "health_check", "platform": "facebook_marketplace"})
            return False