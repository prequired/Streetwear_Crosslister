import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

# Add project root to path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.listing_data import ListingData
from src.models.sale_data import SaleData


@pytest.fixture
def sample_listing_data():
    """Sample listing data for testing"""
    return ListingData(
        item_id="test_item_001",
        platform="mercari",
        platform_listing_id="",
        title="Supreme Box Logo Hoodie",
        description="Authentic Supreme Box Logo Hoodie in excellent condition",
        price=250.00,
        quantity=1,
        condition="Excellent",
        size="L",
        brand="Supreme",
        category="Clothing",
        photos=[
            "https://example.com/photo1.jpg",
            "https://example.com/photo2.jpg"
        ]
    )


@pytest.fixture
def sample_sale_data():
    """Sample sale data for testing"""
    return SaleData(
        sale_id="sale_001",
        listing_id="listing_001",
        buyer_info={"username": "test_buyer", "rating": 4.8},
        sale_date=datetime.now(),
        gross_amount=250.00,
        fees=32.25,
        net_amount=217.75,
        platform="mercari"
    )


@pytest.fixture
def mercari_config():
    """Mercari platform configuration for testing"""
    return {
        "enabled": True,
        "api_key": "test_api_key",
        "secret": "test_secret",
        "access_token": "test_access_token",
        "sandbox": True,
        "rate_limit": {
            "requests_per_minute": 100,
            "burst_limit": 10
        },
        "retry_config": {
            "max_retries": 3,
            "backoff_factor": 2,
            "retry_on_status": [429, 500, 502, 503, 504]
        }
    }


@pytest.fixture
def vinted_config():
    """Vinted platform configuration for testing"""
    return {
        "enabled": False,
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "rate_limit": {
            "requests_per_minute": 60,
            "burst_limit": 5
        },
        "retry_config": {
            "max_retries": 3,
            "backoff_factor": 2,
            "retry_on_status": [429, 500, 502, 503, 504]
        }
    }


@pytest.fixture
def test_config(mercari_config, vinted_config):
    """Complete test configuration"""
    return {
        "platforms": {
            "mercari": mercari_config,
            "vinted": vinted_config
        },
        "global": {
            "default_currency": "USD",
            "max_photos_per_listing": 10,
            "photo_upload_timeout": 30,
            "sync_interval_minutes": 60,
            "batch_size": 50,
            "max_workers": 5
        },
        "logging": {
            "level": "INFO",
            "file": "logs/test.log"
        }
    }


@pytest.fixture
def mock_api_responses():
    """Mock API responses for testing"""
    return {
        "mercari": {
            "auth_success": {
                "data": {
                    "id": "12345",
                    "username": "test_user",
                    "email": "test@example.com"
                }
            },
            "create_listing_success": {
                "data": {
                    "id": "listing_12345",
                    "name": "Supreme Box Logo Hoodie",
                    "description": "Authentic Supreme Box Logo Hoodie",
                    "price": 25000,  # in cents
                    "status": "active",
                    "url": "https://mercari.com/item/listing_12345"
                }
            },
            "update_listing_success": {
                "data": {
                    "id": "listing_12345",
                    "updated": True
                }
            },
            "fetch_listings_success": {
                "data": [
                    {
                        "id": "listing_12345",
                        "name": "Supreme Box Logo Hoodie",
                        "description": "Authentic Supreme Box Logo Hoodie",
                        "price": 25000,
                        "status": "active",
                        "condition": "good",
                        "size": "L",
                        "brand": "Supreme",
                        "category": "clothing",
                        "photos": ["https://example.com/photo1.jpg"],
                        "url": "https://mercari.com/item/listing_12345",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ]
            },
            "fetch_sales_success": {
                "data": [
                    {
                        "id": "sale_12345",
                        "item_id": "listing_12345",
                        "price": 25000,
                        "sold_at": "2024-01-15T10:30:00Z",
                        "buyer": {
                            "username": "buyer_user",
                            "rating": 4.8
                        }
                    }
                ]
            }
        }
    }


@pytest.fixture
def mock_requests_session():
    """Mock requests session for testing"""
    session = Mock()
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"data": {"id": "test_id"}}
    session.get.return_value = response
    session.post.return_value = response
    session.put.return_value = response
    session.delete.return_value = response
    return session