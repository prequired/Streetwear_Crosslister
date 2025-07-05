import pytest
import requests_mock
from unittest.mock import patch, Mock

from src.platforms.mercari import MercariPlatform
from src.models.listing_data import ListingData


class TestMercariPlatform:
    
    def test_init(self, mercari_config):
        """Test MercariPlatform initialization"""
        platform = MercariPlatform(mercari_config)
        
        assert platform.api_key == "test_api_key"
        assert platform.secret == "test_secret"
        assert platform.access_token == "test_access_token"
        assert platform.sandbox is True
        assert platform.base_url == "https://api-sandbox.mercari.com/v1"
    
    def test_authenticate_success(self, mercari_config, mock_api_responses):
        """Test successful authentication"""
        platform = MercariPlatform(mercari_config)
        
        with requests_mock.Mocker() as m:
            m.get(
                "https://api-sandbox.mercari.com/v1/user/profile",
                json=mock_api_responses["mercari"]["auth_success"],
                status_code=200
            )
            
            result = platform.authenticate()
            assert result is True
            assert platform.authenticated is True
    
    def test_authenticate_failure(self, mercari_config):
        """Test failed authentication"""
        platform = MercariPlatform(mercari_config)
        
        with requests_mock.Mocker() as m:
            m.get(
                "https://api-sandbox.mercari.com/v1/user/profile",
                json={"error": "Invalid credentials"},
                status_code=401
            )
            
            result = platform.authenticate()
            assert result is False
            assert platform.authenticated is False
    
    def test_list_item_success(self, mercari_config, sample_listing_data, mock_api_responses):
        """Test successful item listing"""
        platform = MercariPlatform(mercari_config)
        platform.authenticated = True
        
        with requests_mock.Mocker() as m:
            m.post(
                "https://api-sandbox.mercari.com/v1/items",
                json=mock_api_responses["mercari"]["create_listing_success"],
                status_code=201
            )
            
            listing_id = platform.list_item(sample_listing_data)
            assert listing_id == "listing_12345"
    
    def test_list_item_not_authenticated(self, mercari_config, sample_listing_data, mock_api_responses):
        """Test listing item when not authenticated"""
        platform = MercariPlatform(mercari_config)
        platform.authenticated = False
        
        with requests_mock.Mocker() as m:
            # Mock authentication call
            m.get(
                "https://api-sandbox.mercari.com/v1/user/profile",
                json=mock_api_responses["mercari"]["auth_success"],
                status_code=200
            )
            
            # Mock listing creation
            m.post(
                "https://api-sandbox.mercari.com/v1/items",
                json=mock_api_responses["mercari"]["create_listing_success"],
                status_code=201
            )
            
            listing_id = platform.list_item(sample_listing_data)
            assert listing_id == "listing_12345"
            assert platform.authenticated is True
    
    def test_list_item_invalid_data(self, mercari_config):
        """Test listing item with invalid data"""
        platform = MercariPlatform(mercari_config)
        platform.authenticated = True
        
        # Create invalid listing data
        invalid_listing = ListingData(
            item_id="",  # Invalid - empty item_id
            platform="mercari",
            platform_listing_id="",
            title="",  # Invalid - empty title
            description="Test",
            price=0,  # Invalid - zero price
            quantity=1,
            condition="Good"
        )
        
        with pytest.raises(ValueError):
            platform.list_item(invalid_listing)
    
    def test_update_listing_success(self, mercari_config, sample_listing_data, mock_api_responses):
        """Test successful listing update"""
        platform = MercariPlatform(mercari_config)
        platform.authenticated = True
        
        with requests_mock.Mocker() as m:
            m.put(
                "https://api-sandbox.mercari.com/v1/items/listing_12345",
                json=mock_api_responses["mercari"]["update_listing_success"],
                status_code=200
            )
            
            result = platform.update_listing("listing_12345", sample_listing_data)
            assert result["success"] is True
            assert result["listing_id"] == "listing_12345"
    
    def test_delete_listing_success(self, mercari_config):
        """Test successful listing deletion"""
        platform = MercariPlatform(mercari_config)
        platform.authenticated = True
        
        with requests_mock.Mocker() as m:
            m.delete(
                "https://api-sandbox.mercari.com/v1/items/listing_12345",
                status_code=204
            )
            
            result = platform.delete_listing("listing_12345")
            assert result is True
    
    def test_fetch_listings_success(self, mercari_config, mock_api_responses):
        """Test successful listings fetch"""
        platform = MercariPlatform(mercari_config)
        platform.authenticated = True
        
        with requests_mock.Mocker() as m:
            m.get(
                "https://api-sandbox.mercari.com/v1/items",
                json=mock_api_responses["mercari"]["fetch_listings_success"],
                status_code=200
            )
            
            listings = platform.fetch_listings()
            assert len(listings) == 1
            assert isinstance(listings[0], ListingData)
            assert listings[0].title == "Supreme Box Logo Hoodie"
            assert listings[0].price == 250.00  # Converted from cents
    
    def test_fetch_sales_success(self, mercari_config, mock_api_responses):
        """Test successful sales fetch"""
        platform = MercariPlatform(mercari_config)
        platform.authenticated = True
        
        with requests_mock.Mocker() as m:
            m.get(
                "https://api-sandbox.mercari.com/v1/sales",
                json=mock_api_responses["mercari"]["fetch_sales_success"],
                status_code=200
            )
            
            sales = platform.fetch_sales()
            assert len(sales) == 1
            assert sales[0].gross_amount == 250.00  # Converted from cents
            assert sales[0].platform == "mercari"
    
    def test_get_platform_fees(self, mercari_config):
        """Test platform fee calculation"""
        platform = MercariPlatform(mercari_config)
        
        sale_amount = 100.00
        fees = platform.get_platform_fees(sale_amount)
        
        # 10% platform fee + 2.9% payment fee
        expected_fees = (100.00 * 0.10) + (100.00 * 0.029)
        assert fees == expected_fees
    
    def test_condition_mapping(self, mercari_config):
        """Test condition mapping"""
        platform = MercariPlatform(mercari_config)
        
        assert platform.map_condition("New") == "new"
        assert platform.map_condition("Like New") == "like_new"
        assert platform.map_condition("Excellent") == "good"
        assert platform.map_condition("Good") == "good"
        assert platform.map_condition("Fair") == "fair"
        assert platform.map_condition("Poor") == "poor"
        assert platform.map_condition("Unknown") == "good"  # Default
    
    def test_category_mapping(self, mercari_config):
        """Test category mapping"""
        platform = MercariPlatform(mercari_config)
        
        assert platform.map_category("Clothing") == "clothing"
        assert platform.map_category("Shoes") == "shoes"
        assert platform.map_category("Accessories") == "accessories"
        assert platform.map_category("Bags") == "bags"
        assert platform.map_category("Unknown") == "other"  # Default
    
    def test_get_headers(self, mercari_config):
        """Test getting request headers"""
        platform = MercariPlatform(mercari_config)
        headers = platform.get_headers()
        
        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "test_api_key"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers
    
    def test_health_check_success(self, mercari_config, mock_api_responses):
        """Test successful health check"""
        platform = MercariPlatform(mercari_config)
        
        with requests_mock.Mocker() as m:
            m.get(
                "https://api-sandbox.mercari.com/v1/user/profile",
                json=mock_api_responses["mercari"]["auth_success"],
                status_code=200
            )
            
            result = platform.health_check()
            assert result is True
    
    def test_health_check_failure(self, mercari_config):
        """Test failed health check"""
        platform = MercariPlatform(mercari_config)
        
        with requests_mock.Mocker() as m:
            m.get(
                "https://api-sandbox.mercari.com/v1/user/profile",
                json={"error": "Service unavailable"},
                status_code=503
            )
            
            result = platform.health_check()
            assert result is False