import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.cross_listing_service import CrossListingService
from src.models.listing_data import ListingData
from src.models.sale_data import SaleData


class TestCrossListingService:
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_init(self, mock_config_manager, test_config):
        """Test CrossListingService initialization"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        assert len(service.platforms) == 1  # Only Mercari enabled in test config
        assert "mercari" in service.platforms
        assert service.max_workers == 5
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_create_cross_listing_success(self, mock_config_manager, test_config, sample_listing_data):
        """Test successful cross-listing creation"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock the platform
        mock_platform = Mock()
        mock_platform.list_item.return_value = "listing_12345"
        service.platforms["mercari"] = mock_platform
        
        result = service.create_cross_listing(sample_listing_data, ["mercari"])
        
        assert result["success"] is True
        assert result["listing_ids"]["mercari"] == "listing_12345"
        assert "mercari" in result["successful_platforms"]
        assert len(result["failed_platforms"]) == 0
        assert result["item_id"] == sample_listing_data.item_id
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_create_cross_listing_from_dict(self, mock_config_manager, test_config, sample_listing_data):
        """Test cross-listing creation from dictionary data"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock the platform
        mock_platform = Mock()
        mock_platform.list_item.return_value = "listing_12345"
        service.platforms["mercari"] = mock_platform
        
        # Convert to dict and test
        listing_dict = sample_listing_data.to_dict()
        result = service.create_cross_listing(listing_dict, ["mercari"])
        
        assert result["success"] is True
        assert result["listing_ids"]["mercari"] == "listing_12345"
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_create_cross_listing_invalid_data(self, mock_config_manager, test_config):
        """Test cross-listing creation with invalid data"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Create invalid listing data
        invalid_listing = ListingData(
            item_id="",  # Invalid
            platform="mercari",
            platform_listing_id="",
            title="",  # Invalid
            description="Test",
            price=0,  # Invalid
            quantity=1,
            condition="Good"
        )
        
        result = service.create_cross_listing(invalid_listing, ["mercari"])
        
        assert result["success"] is False
        assert "Invalid listing data" in result["error"]
        assert len(result["successful_platforms"]) == 0
        assert "mercari" in result["failed_platforms"]
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_create_cross_listing_no_platforms(self, mock_config_manager, test_config, sample_listing_data):
        """Test cross-listing creation with no available platforms"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        result = service.create_cross_listing(sample_listing_data, ["invalid_platform"])
        
        assert result["success"] is False
        assert "No available platforms" in result["error"]
        assert len(result["successful_platforms"]) == 0
        assert "invalid_platform" in result["failed_platforms"]
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_create_cross_listing_partial_failure(self, mock_config_manager, test_config, sample_listing_data):
        """Test cross-listing creation with partial failure"""
        # Add vinted to test config as enabled
        test_config["platforms"]["vinted"]["enabled"] = True
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock platforms
        mock_mercari = Mock()
        mock_mercari.list_item.return_value = "listing_12345"
        service.platforms["mercari"] = mock_mercari
        
        mock_vinted = Mock()
        mock_vinted.list_item.side_effect = Exception("API Error")
        service.platforms["vinted"] = mock_vinted
        
        result = service.create_cross_listing(sample_listing_data, ["mercari", "vinted"])
        
        assert result["success"] is True  # At least one succeeded
        assert result["partial_success"] is True
        assert result["listing_ids"]["mercari"] == "listing_12345"
        assert "mercari" in result["successful_platforms"]
        assert "vinted" in result["failed_platforms"]
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_update_cross_listing(self, mock_config_manager, test_config):
        """Test cross-listing update"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock platform listings lookup
        service._get_platform_listings = Mock(return_value={"mercari": "listing_12345"})
        
        # Mock the platform
        mock_platform = Mock()
        mock_platform.update_listing.return_value = {"success": True}
        service.platforms["mercari"] = mock_platform
        
        updates = {"price": 200.00, "title": "Updated Title"}
        result = service.update_cross_listing("item_001", updates)
        
        assert result["success"] is True
        assert "mercari" in result["successful_platforms"]
        assert len(result["failed_platforms"]) == 0
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_delete_cross_listing(self, mock_config_manager, test_config):
        """Test cross-listing deletion"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock platform listings lookup
        service._get_platform_listings = Mock(return_value={"mercari": "listing_12345"})
        
        # Mock the platform
        mock_platform = Mock()
        mock_platform.delete_listing.return_value = True
        service.platforms["mercari"] = mock_platform
        
        result = service.delete_cross_listing("item_001")
        
        assert result["success"] is True
        assert "mercari" in result["successful_platforms"]
        assert len(result["failed_platforms"]) == 0
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_sync_all_listings(self, mock_config_manager, test_config):
        """Test syncing all listings"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock the platform
        mock_platform = Mock()
        mock_platform.fetch_listings.return_value = [Mock(), Mock(), Mock()]  # 3 listings
        service.platforms["mercari"] = mock_platform
        
        result = service.sync_all_listings()
        
        assert result["success"] is True
        assert result["total_synced"] == 3
        assert result["total_conflicts"] == 0
        assert "mercari" in result["platform_results"]
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_get_sales_report(self, mock_config_manager, test_config):
        """Test generating sales report"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock sales data
        mock_sales = [
            SaleData(
                sale_id="sale_001",
                listing_id="listing_001",
                buyer_info={"username": "buyer1"},
                sale_date=datetime.now(),
                gross_amount=100.00,
                fees=15.00,
                net_amount=85.00,
                platform="mercari"
            ),
            SaleData(
                sale_id="sale_002",
                listing_id="listing_002",
                buyer_info={"username": "buyer2"},
                sale_date=datetime.now(),
                gross_amount=200.00,
                fees=30.00,
                net_amount=170.00,
                platform="mercari"
            )
        ]
        
        # Mock the platform
        mock_platform = Mock()
        mock_platform.fetch_sales.return_value = mock_sales
        service.platforms["mercari"] = mock_platform
        
        # Test with default date range (last 30 days)
        result = service.get_sales_report()
        
        assert result["summary"]["total_sales"] == 2
        assert result["summary"]["total_gross"] == 300.00
        assert result["summary"]["total_fees"] == 45.00
        assert result["summary"]["total_net"] == 255.00
        assert result["summary"]["average_sale"] == 150.00
        assert "mercari" in result["platform_breakdown"]
        assert result["platform_breakdown"]["mercari"]["sales_count"] == 2
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_get_sales_report_custom_date_range(self, mock_config_manager, test_config):
        """Test generating sales report with custom date range"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock the platform
        mock_platform = Mock()
        mock_platform.fetch_sales.return_value = []
        service.platforms["mercari"] = mock_platform
        
        # Test with custom date range
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        date_range = (start_date, end_date)
        
        result = service.get_sales_report(date_range)
        
        assert result["date_range"]["start"] == start_date.isoformat()
        assert result["date_range"]["end"] == end_date.isoformat()
        assert result["summary"]["total_sales"] == 0
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_health_check(self, mock_config_manager, test_config):
        """Test health check"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock the platform
        mock_platform = Mock()
        mock_platform.health_check.return_value = True
        service.platforms["mercari"] = mock_platform
        
        result = service.health_check()
        
        assert result["overall_healthy"] is True
        assert result["platforms"]["mercari"]["healthy"] is True
        assert "duration" in result
        assert "timestamp" in result
    
    @patch('src.services.cross_listing_service.ConfigManager')
    def test_health_check_with_failure(self, mock_config_manager, test_config):
        """Test health check with platform failure"""
        mock_config_manager.return_value.load_config.return_value = test_config
        
        service = CrossListingService()
        
        # Mock the platform with failure
        mock_platform = Mock()
        mock_platform.health_check.side_effect = Exception("Connection failed")
        service.platforms["mercari"] = mock_platform
        
        result = service.health_check()
        
        assert result["overall_healthy"] is False
        assert result["platforms"]["mercari"]["healthy"] is False
        assert "Connection failed" in result["platforms"]["mercari"]["error"]