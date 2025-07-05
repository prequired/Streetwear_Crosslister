import pytest
from unittest.mock import Mock, patch, MagicMock

from src.platforms.vinted import VintedPlatform
from src.models.listing_data import ListingData
from src.utils.oauth_manager import VintedOAuthManager


class TestVintedPlatform:
    
    def test_init(self, vinted_config):
        """Test VintedPlatform initialization"""
        platform = VintedPlatform(vinted_config)
        
        assert platform.client_id == "test_client_id"
        assert platform.client_secret == "test_client_secret"
        assert platform.access_token == "test_access_token"
        assert platform.refresh_token == "test_refresh_token"
        assert platform.base_url == "https://api.vinted.com/v1"
        assert isinstance(platform.oauth_manager, VintedOAuthManager)
    
    @patch('src.platforms.vinted.requests.get')
    def test_authenticate_success(self, mock_get, vinted_config):
        """Test successful authentication"""
        platform = VintedPlatform(vinted_config)
        
        # Mock OAuth manager
        platform.oauth_manager.is_token_valid = Mock(return_value=True)
        platform.oauth_manager.get_authorization_header = Mock(return_value={'Authorization': 'Bearer test_token'})
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'user': {
                'id': 123,
                'login': 'test_user'
            }
        }
        mock_get.return_value = mock_response
        
        result = platform.authenticate()
        assert result is True
        assert platform.authenticated is True
    
    @patch('src.platforms.vinted.requests.get')
    def test_authenticate_invalid_token(self, mock_get, vinted_config):
        """Test authentication with invalid token"""
        platform = VintedPlatform(vinted_config)
        
        # Mock OAuth manager with invalid token
        platform.oauth_manager.is_token_valid = Mock(return_value=False)
        
        result = platform.authenticate()
        assert result is False
        assert platform.authenticated is False
    
    @patch('src.platforms.vinted.requests.post')
    def test_list_item_success(self, mock_post, vinted_config, sample_listing_data):
        """Test successful item listing"""
        platform = VintedPlatform(vinted_config)
        platform.authenticated = True
        
        # Mock photo upload
        platform._upload_photos = Mock(return_value=[1, 2, 3])
        platform._get_category_id = Mock(return_value=1)
        platform._get_brand_id = Mock(return_value=101)
        platform._get_size_id = Mock(return_value=201)
        platform._get_condition_id = Mock(return_value=3)
        
        # Mock OAuth manager
        platform.oauth_manager.get_authorization_header = Mock(return_value={'Authorization': 'Bearer test_token'})
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'item': {
                'id': 12345,
                'title': 'Supreme Box Logo Hoodie'
            }
        }
        mock_post.return_value = mock_response
        
        listing_id = platform.list_item(sample_listing_data)
        assert listing_id == "12345"
    
    @patch('src.platforms.vinted.requests.get')
    def test_upload_single_photo(self, mock_get, vinted_config):
        """Test photo upload functionality"""
        platform = VintedPlatform(vinted_config)
        platform.authenticated = True
        
        # Mock OAuth manager
        platform.oauth_manager.get_authorization_header = Mock(return_value={'Authorization': 'Bearer test_token'})
        
        # Mock photo download
        mock_photo_response = Mock()
        mock_photo_response.status_code = 200
        mock_photo_response.content = b'fake_image_data'
        
        # Mock photo upload response
        mock_upload_response = Mock()
        mock_upload_response.status_code = 201
        mock_upload_response.json.return_value = {
            'photo': {
                'id': 123
            }
        }
        
        with patch('src.platforms.vinted.requests.post', return_value=mock_upload_response):
            mock_get.return_value = mock_photo_response
            
            photo_id = platform._upload_single_photo("https://example.com/photo.jpg")
            assert photo_id == 123
    
    @patch('src.platforms.vinted.requests.put')
    def test_update_listing_success(self, mock_put, vinted_config, sample_listing_data):
        """Test successful listing update"""
        platform = VintedPlatform(vinted_config)
        platform.authenticated = True
        
        # Mock OAuth manager
        platform.oauth_manager.get_authorization_header = Mock(return_value={'Authorization': 'Bearer test_token'})
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'item': {
                'id': 12345,
                'updated': True
            }
        }
        mock_put.return_value = mock_response
        
        result = platform.update_listing("12345", sample_listing_data)
        assert result["success"] is True
        assert result["listing_id"] == "12345"
    
    @patch('src.platforms.vinted.requests.delete')
    def test_delete_listing_success(self, mock_delete, vinted_config):
        """Test successful listing deletion"""
        platform = VintedPlatform(vinted_config)
        platform.authenticated = True
        
        # Mock OAuth manager
        platform.oauth_manager.get_authorization_header = Mock(return_value={'Authorization': 'Bearer test_token'})
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response
        
        result = platform.delete_listing("12345")
        assert result is True
    
    @patch('src.platforms.vinted.requests.get')
    def test_fetch_listings_success(self, mock_get, vinted_config):
        """Test successful listings fetch"""
        platform = VintedPlatform(vinted_config)
        platform.authenticated = True
        
        # Mock OAuth manager
        platform.oauth_manager.get_authorization_header = Mock(return_value={'Authorization': 'Bearer test_token'})
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {
                    'id': 12345,
                    'title': 'Supreme Box Logo Hoodie',
                    'description': 'Authentic Supreme hoodie',
                    'price': 250.0,
                    'status': 'very_good',
                    'size_title': 'L',
                    'brand_title': 'Supreme',
                    'category': 'clothing',
                    'photos': [{'url': 'https://example.com/photo1.jpg'}],
                    'url': 'https://vinted.com/items/12345',
                    'can_be_sold': True,
                    'created_at_ts': 1642248600,
                    'updated_at_ts': 1642248600
                }
            ]
        }
        mock_get.return_value = mock_response
        
        listings = platform.fetch_listings()
        assert len(listings) == 1
        assert isinstance(listings[0], ListingData)
        assert listings[0].title == "Supreme Box Logo Hoodie"
        assert listings[0].price == 250.0
        assert listings[0].platform == "vinted"
    
    @patch('src.platforms.vinted.requests.get')
    def test_fetch_sales_success(self, mock_get, vinted_config):
        """Test successful sales fetch"""
        platform = VintedPlatform(vinted_config)
        platform.authenticated = True
        
        # Mock OAuth manager
        platform.oauth_manager.get_authorization_header = Mock(return_value={'Authorization': 'Bearer test_token'})
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'transactions': [
                {
                    'id': 67890,
                    'item_id': 12345,
                    'status': 'sold',
                    'total_item_price': 250.0,
                    'created_at': '2024-01-15T10:30:00Z',
                    'buyer': {
                        'login': 'buyer_user'
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        sales = platform.fetch_sales()
        assert len(sales) == 1
        assert sales[0].gross_amount == 250.0
        assert sales[0].platform == "vinted"
    
    def test_get_platform_fees(self, vinted_config):
        """Test platform fee calculation"""
        platform = VintedPlatform(vinted_config)
        
        sale_amount = 100.00
        fees = platform.get_platform_fees(sale_amount)
        
        # 3% buyer protection + 5% platform fee
        expected_fees = (100.00 * 0.03) + (100.00 * 0.05)
        assert fees == expected_fees
    
    def test_condition_mapping(self, vinted_config):
        """Test condition mapping"""
        platform = VintedPlatform(vinted_config)
        
        assert platform.map_condition("New") == "brand_new_with_tag"
        assert platform.map_condition("Like New") == "brand_new_without_tag"
        assert platform.map_condition("Excellent") == "very_good"
        assert platform.map_condition("Good") == "good"
        assert platform.map_condition("Fair") == "satisfactory"
        assert platform.map_condition("Poor") == "poor"
        assert platform.map_condition("Unknown") == "good"  # Default
    
    def test_category_mapping(self, vinted_config):
        """Test category mapping"""
        platform = VintedPlatform(vinted_config)
        
        assert platform.map_category("Clothing") == "clothing"
        assert platform.map_category("Shoes") == "shoes"
        assert platform.map_category("Accessories") == "accessories"
        assert platform.map_category("Bags") == "bags"
        assert platform.map_category("Unknown") == "clothing"  # Default
    
    def test_get_headers(self, vinted_config):
        """Test getting request headers"""
        platform = VintedPlatform(vinted_config)
        headers = platform.get_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert headers["Accept-Language"] == "en"
        assert "User-Agent" in headers
    
    def test_parse_date_timestamp(self, vinted_config):
        """Test parsing timestamp to datetime"""
        platform = VintedPlatform(vinted_config)
        
        timestamp = 1642248600  # 2022-01-15 10:30:00
        parsed_date = platform._parse_date(timestamp)
        
        assert parsed_date is not None
        assert parsed_date.year == 2022
        assert parsed_date.month == 1
        assert parsed_date.day == 15
    
    def test_parse_date_string(self, vinted_config):
        """Test parsing ISO string to datetime"""
        platform = VintedPlatform(vinted_config)
        
        date_string = "2024-01-15T10:30:00Z"
        parsed_date = platform._parse_date(date_string)
        
        assert parsed_date is not None
        assert parsed_date.year == 2024
        assert parsed_date.month == 1
        assert parsed_date.day == 15