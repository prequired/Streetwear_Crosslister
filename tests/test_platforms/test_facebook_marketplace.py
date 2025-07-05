import pytest
from unittest.mock import Mock, patch

from src.platforms.facebook_marketplace import FacebookMarketplacePlatform
from src.models.listing_data import ListingData


@pytest.fixture
def facebook_config():
    """Facebook platform configuration for testing"""
    return {
        "enabled": False,
        "app_id": "test_app_id",
        "app_secret": "test_app_secret",
        "access_token": "test_access_token",
        "page_id": "test_page_id",
        "catalog_id": "test_catalog_id",
        "graph_version": "v18.0"
    }


class TestFacebookMarketplacePlatform:
    
    def test_init(self, facebook_config):
        """Test FacebookMarketplacePlatform initialization"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        assert platform.app_id == "test_app_id"
        assert platform.app_secret == "test_app_secret"
        assert platform.access_token == "test_access_token"
        assert platform.page_id == "test_page_id"
        assert platform.catalog_id == "test_catalog_id"
        assert platform.base_url == "https://graph.facebook.com/v18.0"
    
    @patch('src.platforms.facebook_marketplace.requests.get')
    def test_authenticate_success(self, mock_get, facebook_config):
        """Test successful authentication"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '123456789',
            'name': 'Test User'
        }
        mock_get.return_value = mock_response
        
        result = platform.authenticate()
        assert result is True
        assert platform.authenticated is True
    
    @patch('src.platforms.facebook_marketplace.requests.get')
    def test_authenticate_failure(self, mock_get, facebook_config):
        """Test failed authentication"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid access token"
        mock_get.return_value = mock_response
        
        result = platform.authenticate()
        assert result is False
        assert platform.authenticated is False
    
    def test_list_item_success(self, facebook_config, sample_listing_data):
        """Test successful item listing"""
        platform = FacebookMarketplacePlatform(facebook_config)
        platform.authenticated = True
        
        # Mock the two-step listing process
        platform._create_product_in_catalog = Mock(return_value="product_123")
        platform._create_marketplace_listing = Mock(return_value="listing_456")
        
        listing_id = platform.list_item(sample_listing_data)
        assert listing_id == "listing_456"
        
        # Verify both steps were called
        platform._create_product_in_catalog.assert_called_once_with(sample_listing_data)
        platform._create_marketplace_listing.assert_called_once_with("product_123", sample_listing_data)
    
    @patch('src.platforms.facebook_marketplace.requests.post')
    def test_create_product_in_catalog(self, mock_post, facebook_config, sample_listing_data):
        """Test creating product in catalog"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'product_123456'
        }
        mock_post.return_value = mock_response
        
        product_id = platform._create_product_in_catalog(sample_listing_data)
        assert product_id == "product_123456"
        
        # Verify request was made with correct data
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'json' in call_args.kwargs
        payload = call_args.kwargs['json']
        assert payload['name'] == sample_listing_data.title
        assert payload['price'] == int(sample_listing_data.price * 100)  # Price in cents
    
    @patch('src.platforms.facebook_marketplace.requests.post')
    def test_create_marketplace_listing(self, mock_post, facebook_config, sample_listing_data):
        """Test creating marketplace listing"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'listing_789'
        }
        mock_post.return_value = mock_response
        
        listing_id = platform._create_marketplace_listing("product_123", sample_listing_data)
        assert listing_id == "listing_789"
    
    def test_list_item_no_catalog_id(self, sample_listing_data):
        """Test listing item without catalog ID"""
        config = {
            "app_id": "test_app_id",
            "access_token": "test_access_token"
            # No catalog_id
        }
        platform = FacebookMarketplacePlatform(config)
        platform.authenticated = True
        
        with pytest.raises(Exception) as exc_info:
            platform.list_item(sample_listing_data)
        
        assert "Catalog ID not configured" in str(exc_info.value)
    
    @patch('src.platforms.facebook_marketplace.requests.post')
    def test_update_listing_success(self, mock_post, facebook_config, sample_listing_data):
        """Test successful listing update"""
        platform = FacebookMarketplacePlatform(facebook_config)
        platform.authenticated = True
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True
        }
        mock_post.return_value = mock_response
        
        result = platform.update_listing("listing_123", sample_listing_data)
        assert result["success"] is True
        assert result["listing_id"] == "listing_123"
    
    @patch('src.platforms.facebook_marketplace.requests.delete')
    def test_delete_listing_success(self, mock_delete, facebook_config):
        """Test successful listing deletion"""
        platform = FacebookMarketplacePlatform(facebook_config)
        platform.authenticated = True
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response
        
        result = platform.delete_listing("listing_123")
        assert result is True
    
    @patch('src.platforms.facebook_marketplace.requests.get')
    def test_fetch_listings_success(self, mock_get, facebook_config):
        """Test successful listings fetch"""
        platform = FacebookMarketplacePlatform(facebook_config)
        platform.authenticated = True
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    'id': 'product_123',
                    'retailer_id': 'item_001',
                    'name': 'Supreme Box Logo Hoodie',
                    'description': 'Authentic Supreme hoodie',
                    'price': 25000,  # Price in cents
                    'condition': 'GOOD',
                    'category': 'APPAREL',
                    'brand': 'Supreme',
                    'image_url': 'https://example.com/photo1.jpg',
                    'availability': 'in stock',
                    'inventory': 1
                }
            ]
        }
        mock_get.return_value = mock_response
        
        listings = platform.fetch_listings()
        assert len(listings) == 1
        assert isinstance(listings[0], ListingData)
        assert listings[0].title == "Supreme Box Logo Hoodie"
        assert listings[0].price == 250.0  # Converted from cents
        assert listings[0].platform == "facebook_marketplace"
    
    def test_fetch_sales(self, facebook_config):
        """Test sales fetch (limited data)"""
        platform = FacebookMarketplacePlatform(facebook_config)
        platform.authenticated = True
        
        # Facebook Marketplace doesn't provide comprehensive sales data
        sales = platform.fetch_sales()
        assert isinstance(sales, list)
        assert len(sales) == 0  # Should return empty list
    
    def test_get_platform_fees(self, facebook_config):
        """Test platform fee calculation"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        sale_amount = 100.00
        fees = platform.get_platform_fees(sale_amount)
        
        # Facebook doesn't charge fees for organic listings
        assert fees == 0.0
    
    def test_condition_mapping(self, facebook_config):
        """Test condition mapping"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        assert platform.map_condition("New") == "NEW"
        assert platform.map_condition("Like New") == "LIKE_NEW"
        assert platform.map_condition("Excellent") == "GOOD"
        assert platform.map_condition("Good") == "GOOD"
        assert platform.map_condition("Fair") == "FAIR"
        assert platform.map_condition("Poor") == "POOR"
        assert platform.map_condition("Unknown") == "GOOD"  # Default
    
    def test_category_mapping(self, facebook_config):
        """Test category mapping"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        assert platform.map_category("Clothing") == "APPAREL"
        assert platform.map_category("Shoes") == "SHOES"
        assert platform.map_category("Accessories") == "ACCESSORIES"
        assert platform.map_category("Bags") == "BAGS_AND_LUGGAGE"
        assert platform.map_category("Unknown") == "APPAREL"  # Default
    
    def test_get_headers(self, facebook_config):
        """Test getting request headers"""
        platform = FacebookMarketplacePlatform(facebook_config)
        headers = platform.get_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers
    
    @patch('src.platforms.facebook_marketplace.requests.get')
    def test_health_check_success(self, mock_get, facebook_config):
        """Test successful health check"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        # Mock both API and catalog checks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': '123', 'name': 'Test'}
        mock_get.return_value = mock_response
        
        result = platform.health_check()
        assert result is True
    
    @patch('src.platforms.facebook_marketplace.requests.get')
    def test_health_check_failure(self, mock_get, facebook_config):
        """Test failed health check"""
        platform = FacebookMarketplacePlatform(facebook_config)
        
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        result = platform.health_check()
        assert result is False