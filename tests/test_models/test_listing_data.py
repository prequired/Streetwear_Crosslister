import pytest
from datetime import datetime

from src.models.listing_data import ListingData


class TestListingData:
    
    def test_create_listing_data(self, sample_listing_data):
        """Test creating ListingData instance"""
        assert sample_listing_data.item_id == "test_item_001"
        assert sample_listing_data.platform == "mercari"
        assert sample_listing_data.title == "Supreme Box Logo Hoodie"
        assert sample_listing_data.price == 250.00
        assert sample_listing_data.condition == "Excellent"
    
    def test_validate_valid_listing(self, sample_listing_data):
        """Test validation of valid listing data"""
        assert sample_listing_data.validate() is True
    
    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields"""
        # Missing item_id
        listing = ListingData(
            item_id="",
            platform="mercari",
            platform_listing_id="",
            title="Test Title",
            description="Test Description",
            price=100.0,
            quantity=1,
            condition="Good"
        )
        assert listing.validate() is False
        
        # Missing title
        listing.item_id = "test_id"
        listing.title = ""
        assert listing.validate() is False
        
        # Valid now with title set
        listing.title = "Test Title"
        assert listing.validate() is True
    
    def test_validate_invalid_price(self, sample_listing_data):
        """Test validation with invalid price"""
        sample_listing_data.price = 0
        assert sample_listing_data.validate() is False
        
        sample_listing_data.price = -10
        assert sample_listing_data.validate() is False
    
    def test_validate_invalid_quantity(self, sample_listing_data):
        """Test validation with invalid quantity"""
        sample_listing_data.quantity = 0
        assert sample_listing_data.validate() is False
        
        sample_listing_data.quantity = -1
        assert sample_listing_data.validate() is False
    
    def test_validate_invalid_condition(self, sample_listing_data):
        """Test validation with invalid condition"""
        sample_listing_data.condition = "Invalid Condition"
        assert sample_listing_data.validate() is False
        
        # Test valid conditions
        valid_conditions = ['New', 'Like New', 'Excellent', 'Good', 'Fair', 'Poor']
        for condition in valid_conditions:
            sample_listing_data.condition = condition
            assert sample_listing_data.validate() is True
    
    def test_to_dict(self, sample_listing_data):
        """Test converting ListingData to dictionary"""
        data_dict = sample_listing_data.to_dict()
        
        assert isinstance(data_dict, dict)
        assert data_dict['item_id'] == sample_listing_data.item_id
        assert data_dict['title'] == sample_listing_data.title
        assert data_dict['price'] == sample_listing_data.price
        assert data_dict['photos'] == sample_listing_data.photos
        
        # Check datetime serialization
        assert isinstance(data_dict['created_at'], str)
        assert isinstance(data_dict['updated_at'], str)
    
    def test_from_dict(self, sample_listing_data):
        """Test creating ListingData from dictionary"""
        data_dict = sample_listing_data.to_dict()
        restored_listing = ListingData.from_dict(data_dict)
        
        assert restored_listing.item_id == sample_listing_data.item_id
        assert restored_listing.title == sample_listing_data.title
        assert restored_listing.price == sample_listing_data.price
        assert restored_listing.photos == sample_listing_data.photos
        assert isinstance(restored_listing.created_at, datetime)
        assert isinstance(restored_listing.updated_at, datetime)
    
    def test_from_dict_with_string_dates(self):
        """Test creating ListingData from dict with string dates"""
        data_dict = {
            'item_id': 'test_001',
            'platform': 'mercari',
            'platform_listing_id': '',
            'title': 'Test Item',
            'description': 'Test Description',
            'price': 100.0,
            'quantity': 1,
            'condition': 'Good',
            'created_at': '2024-01-15T10:30:00',
            'updated_at': '2024-01-15T11:30:00'
        }
        
        listing = ListingData.from_dict(data_dict)
        
        assert isinstance(listing.created_at, datetime)
        assert isinstance(listing.updated_at, datetime)
        assert listing.created_at.year == 2024
        assert listing.created_at.month == 1
        assert listing.created_at.day == 15