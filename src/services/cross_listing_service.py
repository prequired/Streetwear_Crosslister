import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from ..models.listing_data import ListingData
from ..models.sale_data import SaleData
from ..platforms.base import PlatformBase
from ..platforms.mercari import MercariPlatform
from ..platforms.vinted import VintedPlatform
from ..platforms.facebook_marketplace import FacebookMarketplacePlatform
from ..utils.config_manager import ConfigManager
from ..utils.logger import get_logger


class CrossListingService:
    """Core service for cross-platform listing management"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = get_logger(self.__class__.__name__)
        self.config_manager = ConfigManager()
        self.config = config or self.config_manager.load_config()
        
        self.platforms = self._initialize_platforms()
        self.max_workers = self.config.get('global', {}).get('max_workers', 5)
        
        self.logger.logger.info(f"CrossListingService initialized with {len(self.platforms)} platforms")
    
    def _initialize_platforms(self) -> Dict[str, PlatformBase]:
        """Initialize platform instances based on configuration"""
        platforms = {}
        
        for platform_name, platform_config in self.config.get('platforms', {}).items():
            if not platform_config.get('enabled', False):
                continue
            
            try:
                if platform_name == 'mercari':
                    platforms[platform_name] = MercariPlatform(platform_config)
                elif platform_name == 'vinted':
                    platforms[platform_name] = VintedPlatform(platform_config)
                elif platform_name == 'facebook_marketplace':
                    platforms[platform_name] = FacebookMarketplacePlatform(platform_config)
                else:
                    self.logger.logger.warning(f"Unknown platform: {platform_name}")
                    continue
                
                self.logger.logger.info(f"Initialized platform: {platform_name}")
                
            except Exception as e:
                self.logger.log_error(e, {
                    "operation": "initialize_platform",
                    "platform": platform_name
                })
                continue
        
        return platforms
    
    def create_cross_listing(self, listing_data: Dict[str, Any], 
                           target_platforms: List[str]) -> Dict[str, Any]:
        """Create listings across multiple platforms"""
        start_time = time.time()
        
        # Convert dict to ListingData if needed
        if isinstance(listing_data, dict):
            listing_data = ListingData.from_dict(listing_data)
        
        # Validate listing data
        if not listing_data.validate():
            return {
                "success": False,
                "error": "Invalid listing data",
                "listing_ids": {},
                "failed_platforms": target_platforms,
                "successful_platforms": []
            }
        
        # Filter platforms that are available and enabled
        available_platforms = [p for p in target_platforms if p in self.platforms]
        if not available_platforms:
            return {
                "success": False,
                "error": "No available platforms",
                "listing_ids": {},
                "failed_platforms": target_platforms,
                "successful_platforms": []
            }
        
        listing_ids = {}
        successful_platforms = []
        failed_platforms = []
        
        # Create listings in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_platform = {
                executor.submit(self._create_single_listing, platform_name, listing_data): platform_name
                for platform_name in available_platforms
            }
            
            for future in as_completed(future_to_platform):
                platform_name = future_to_platform[future]
                
                try:
                    result = future.result()
                    if result['success']:
                        listing_ids[platform_name] = result['listing_id']
                        successful_platforms.append(platform_name)
                    else:
                        failed_platforms.append(platform_name)
                        
                except Exception as e:
                    self.logger.log_error(e, {
                        "operation": "create_cross_listing",
                        "platform": platform_name,
                        "item_id": listing_data.item_id
                    })
                    failed_platforms.append(platform_name)
        
        duration = time.time() - start_time
        success = len(successful_platforms) > 0
        partial_success = len(successful_platforms) > 0 and len(failed_platforms) > 0
        
        # Log performance
        self.logger.log_performance(
            operation="create_cross_listing",
            duration=duration,
            items_count=len(available_platforms)
        )
        
        # Log operation result
        self.logger.log_listing_operation(
            operation="cross_create",
            platform="multiple",
            item_id=listing_data.item_id,
            success=success,
            error=f"Failed on {len(failed_platforms)} platforms" if failed_platforms else None
        )
        
        return {
            "success": success,
            "partial_success": partial_success,
            "listing_ids": listing_ids,
            "successful_platforms": successful_platforms,
            "failed_platforms": failed_platforms,
            "duration": duration,
            "item_id": listing_data.item_id
        }
    
    def _create_single_listing(self, platform_name: str, listing_data: ListingData) -> Dict[str, Any]:
        """Create a listing on a single platform"""
        try:
            platform = self.platforms[platform_name]
            listing_id = platform.list_item(listing_data)
            
            return {
                "success": True,
                "listing_id": listing_id,
                "platform": platform_name
            }
            
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "create_single_listing",
                "platform": platform_name,
                "item_id": listing_data.item_id
            })
            
            return {
                "success": False,
                "error": str(e),
                "platform": platform_name
            }
    
    def update_cross_listing(self, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update listings across all platforms for an item"""
        start_time = time.time()
        
        # First, find all platform listings for this item
        # This would typically come from a database lookup
        # For now, we'll simulate this
        platform_listings = self._get_platform_listings(item_id)
        
        if not platform_listings:
            return {
                "success": False,
                "error": "No platform listings found for item",
                "item_id": item_id
            }
        
        # Create updated ListingData with defaults for missing required fields
        # In a real implementation, this would merge with existing data from database
        default_data = {
            "item_id": item_id,
            "platform": "",  # Will be set per platform
            "platform_listing_id": "",  # Will be set per platform
            "title": "Updated Item",
            "description": "Updated description",
            "price": 100.0,
            "quantity": 1,
            "condition": "Good"
        }
        default_data.update(updates)
        listing_data = ListingData(**default_data)
        
        successful_platforms = []
        failed_platforms = []
        
        # Update listings in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_platform = {
                executor.submit(self._update_single_listing, platform_name, listing_id, listing_data): platform_name
                for platform_name, listing_id in platform_listings.items()
            }
            
            for future in as_completed(future_to_platform):
                platform_name = future_to_platform[future]
                
                try:
                    result = future.result()
                    if result['success']:
                        successful_platforms.append(platform_name)
                    else:
                        failed_platforms.append(platform_name)
                        
                except Exception as e:
                    self.logger.log_error(e, {
                        "operation": "update_cross_listing",
                        "platform": platform_name,
                        "item_id": item_id
                    })
                    failed_platforms.append(platform_name)
        
        duration = time.time() - start_time
        success = len(successful_platforms) > 0
        
        # Log performance
        self.logger.log_performance(
            operation="update_cross_listing",
            duration=duration,
            items_count=len(platform_listings)
        )
        
        return {
            "success": success,
            "successful_platforms": successful_platforms,
            "failed_platforms": failed_platforms,
            "duration": duration,
            "item_id": item_id
        }
    
    def _update_single_listing(self, platform_name: str, listing_id: str, 
                              listing_data: ListingData) -> Dict[str, Any]:
        """Update a listing on a single platform"""
        try:
            platform = self.platforms[platform_name]
            result = platform.update_listing(listing_id, listing_data)
            
            return {
                "success": True,
                "result": result,
                "platform": platform_name
            }
            
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "update_single_listing",
                "platform": platform_name,
                "listing_id": listing_id
            })
            
            return {
                "success": False,
                "error": str(e),
                "platform": platform_name
            }
    
    def delete_cross_listing(self, item_id: str) -> Dict[str, Any]:
        """Delete listings across all platforms for an item"""
        start_time = time.time()
        
        # Find all platform listings for this item
        platform_listings = self._get_platform_listings(item_id)
        
        if not platform_listings:
            return {
                "success": False,
                "error": "No platform listings found for item",
                "item_id": item_id
            }
        
        successful_platforms = []
        failed_platforms = []
        
        # Delete listings in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_platform = {
                executor.submit(self._delete_single_listing, platform_name, listing_id): platform_name
                for platform_name, listing_id in platform_listings.items()
            }
            
            for future in as_completed(future_to_platform):
                platform_name = future_to_platform[future]
                
                try:
                    result = future.result()
                    if result['success']:
                        successful_platforms.append(platform_name)
                    else:
                        failed_platforms.append(platform_name)
                        
                except Exception as e:
                    self.logger.log_error(e, {
                        "operation": "delete_cross_listing",
                        "platform": platform_name,
                        "item_id": item_id
                    })
                    failed_platforms.append(platform_name)
        
        duration = time.time() - start_time
        success = len(successful_platforms) > 0
        
        # Log performance
        self.logger.log_performance(
            operation="delete_cross_listing",
            duration=duration,
            items_count=len(platform_listings)
        )
        
        return {
            "success": success,
            "successful_platforms": successful_platforms,
            "failed_platforms": failed_platforms,
            "duration": duration,
            "item_id": item_id
        }
    
    def _delete_single_listing(self, platform_name: str, listing_id: str) -> Dict[str, Any]:
        """Delete a listing on a single platform"""
        try:
            platform = self.platforms[platform_name]
            success = platform.delete_listing(listing_id)
            
            return {
                "success": success,
                "platform": platform_name
            }
            
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "delete_single_listing",
                "platform": platform_name,
                "listing_id": listing_id
            })
            
            return {
                "success": False,
                "error": str(e),
                "platform": platform_name
            }
    
    def sync_all_listings(self) -> Dict[str, Any]:
        """Synchronize all listings across platforms"""
        start_time = time.time()
        
        sync_results = {}
        total_synced = 0
        total_conflicts = 0
        
        for platform_name in self.platforms.keys():
            try:
                result = self._sync_platform_listings(platform_name)
                sync_results[platform_name] = result
                total_synced += result.get('synced_count', 0)
                total_conflicts += result.get('conflicts_count', 0)
                
            except Exception as e:
                self.logger.log_error(e, {
                    "operation": "sync_all_listings",
                    "platform": platform_name
                })
                sync_results[platform_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        duration = time.time() - start_time
        
        # Log sync operation
        self.logger.log_sync_operation(
            operation="sync_all",
            platform="all",
            items_processed=total_synced,
            items_failed=total_conflicts,
            duration=duration
        )
        
        return {
            "success": True,
            "duration": duration,
            "total_synced": total_synced,
            "total_conflicts": total_conflicts,
            "platform_results": sync_results,
            "summary": f"Synced {total_synced} listings with {total_conflicts} conflicts"
        }
    
    def _sync_platform_listings(self, platform_name: str) -> Dict[str, Any]:
        """Sync listings for a specific platform"""
        try:
            platform = self.platforms[platform_name]
            
            # Fetch current listings from platform
            platform_listings = platform.fetch_listings()
            
            # TODO: Compare with local database and resolve conflicts
            # For now, just return stats
            
            return {
                "success": True,
                "synced_count": len(platform_listings),
                "conflicts_count": 0,
                "platform": platform_name
            }
            
        except Exception as e:
            self.logger.log_error(e, {
                "operation": "sync_platform_listings",
                "platform": platform_name
            })
            raise
    
    def get_sales_report(self, date_range: Tuple[datetime, datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive sales report across all platforms"""
        start_time = time.time()
        
        if date_range is None:
            # Default to last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            date_range = (start_date, end_date)
        
        all_sales = []
        platform_sales = {}
        
        # Fetch sales from all platforms
        for platform_name in self.platforms.keys():
            try:
                platform = self.platforms[platform_name]
                sales = platform.fetch_sales(date_range)
                
                platform_sales[platform_name] = sales
                all_sales.extend(sales)
                
            except Exception as e:
                self.logger.log_error(e, {
                    "operation": "get_sales_report",
                    "platform": platform_name
                })
                platform_sales[platform_name] = []
        
        # Calculate totals
        total_sales = len(all_sales)
        total_gross = sum(sale.gross_amount for sale in all_sales)
        total_fees = sum(sale.fees for sale in all_sales)
        total_net = sum(sale.net_amount for sale in all_sales)
        
        # Platform breakdown
        platform_breakdown = {}
        for platform_name, sales in platform_sales.items():
            platform_breakdown[platform_name] = {
                "sales_count": len(sales),
                "gross_amount": sum(sale.gross_amount for sale in sales),
                "fees": sum(sale.fees for sale in sales),
                "net_amount": sum(sale.net_amount for sale in sales)
            }
        
        duration = time.time() - start_time
        
        # Log performance
        self.logger.log_performance(
            operation="get_sales_report",
            duration=duration,
            items_count=total_sales
        )
        
        return {
            "date_range": {
                "start": date_range[0].isoformat(),
                "end": date_range[1].isoformat()
            },
            "summary": {
                "total_sales": total_sales,
                "total_gross": round(total_gross, 2),
                "total_fees": round(total_fees, 2),
                "total_net": round(total_net, 2),
                "average_sale": round(total_gross / total_sales, 2) if total_sales > 0 else 0,
                "profit_margin": round((total_net / total_gross) * 100, 2) if total_gross > 0 else 0
            },
            "platform_breakdown": platform_breakdown,
            "duration": duration
        }
    
    def _get_platform_listings(self, item_id: str) -> Dict[str, str]:
        """Get platform listing IDs for an item (mock implementation)"""
        # TODO: Implement actual database lookup
        # For now, return empty dict
        return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all platforms"""
        start_time = time.time()
        
        platform_health = {}
        overall_healthy = True
        
        for platform_name, platform in self.platforms.items():
            try:
                health_start = time.time()
                is_healthy = platform.health_check()
                health_duration = time.time() - health_start
                
                platform_health[platform_name] = {
                    "healthy": is_healthy,
                    "response_time": round(health_duration, 3),
                    "error": None
                }
                
                if not is_healthy:
                    overall_healthy = False
                    
            except Exception as e:
                platform_health[platform_name] = {
                    "healthy": False,
                    "response_time": None,
                    "error": str(e)
                }
                overall_healthy = False
        
        duration = time.time() - start_time
        
        return {
            "overall_healthy": overall_healthy,
            "platforms": platform_health,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }