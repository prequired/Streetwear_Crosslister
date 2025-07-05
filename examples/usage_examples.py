#!/usr/bin/env python3
"""
Streetwear Inventory Cross-Listing System
Usage Examples and Demonstrations
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.cross_listing_service import CrossListingService
from src.models.listing_data import ListingData
from src.utils.config_manager import ConfigManager
from datetime import datetime


def example_cross_listing():
    """Example: Create a cross-platform listing"""
    print("=== Cross-Platform Listing Example ===")
    
    # Initialize service
    service = CrossListingService()
    
    # Create sample listing data
    listing_data = ListingData(
        item_id="supreme_hoodie_001",
        platform="",  # Will be set per platform
        platform_listing_id="",
        title="Supreme Box Logo Hoodie - Black/White",
        description="""
        Authentic Supreme Box Logo Hoodie in excellent condition.
        
        Features:
        - 100% Cotton fleece
        - Kangaroo pocket
        - Ribbed cuffs and waistband
        - Classic Supreme box logo
        
        Condition: Excellent - worn a few times, no flaws
        Authenticity: 100% authentic, purchased from Supreme
        """.strip(),
        price=450.00,
        quantity=1,
        condition="Excellent",
        size="L",
        brand="Supreme",
        category="Clothing",
        photos=[
            "https://example.com/supreme-hoodie-front.jpg",
            "https://example.com/supreme-hoodie-back.jpg",
            "https://example.com/supreme-hoodie-tag.jpg",
            "https://example.com/supreme-hoodie-details.jpg"
        ]
    )
    
    # Create cross-platform listing
    try:
        print(f"Creating listing for: {listing_data.title}")
        print(f"Price: ${listing_data.price}")
        print(f"Platforms: mercari, vinted, facebook_marketplace")
        
        result = service.create_cross_listing(
            listing_data,
            target_platforms=["mercari", "vinted", "facebook_marketplace"]
        )
        
        print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
        if result['success']:
            print(f"Duration: {result['duration']:.2f} seconds")
            if result['listing_ids']:
                print("Platform Listing IDs:")
                for platform, listing_id in result['listing_ids'].items():
                    print(f"  - {platform}: {listing_id}")
        
        if result['failed_platforms']:
            print(f"Failed platforms: {', '.join(result['failed_platforms'])}")
            
    except Exception as e:
        print(f"Error: {e}")


def example_sales_report():
    """Example: Generate sales report"""
    print("\n=== Sales Report Example ===")
    
    # Initialize service
    service = CrossListingService()
    
    try:
        print("Generating sales report for last 30 days...")
        
        report = service.get_sales_report()
        
        print(f"\nSales Summary:")
        summary = report['summary']
        print(f"  Total Sales: {summary['total_sales']}")
        print(f"  Gross Revenue: ${summary['total_gross']:.2f}")
        print(f"  Total Fees: ${summary['total_fees']:.2f}")
        print(f"  Net Revenue: ${summary['total_net']:.2f}")
        print(f"  Average Sale: ${summary['average_sale']:.2f}")
        print(f"  Profit Margin: {summary['profit_margin']:.1f}%")
        
        print(f"\nPlatform Breakdown:")
        for platform, stats in report['platform_breakdown'].items():
            print(f"  {platform}:")
            print(f"    Sales: {stats['sales_count']}")
            print(f"    Gross: ${stats['gross_amount']:.2f}")
            print(f"    Net: ${stats['net_amount']:.2f}")
        
        print(f"\nReport generated in {report['duration']:.2f} seconds")
        
    except Exception as e:
        print(f"Error: {e}")


def example_platform_health():
    """Example: Check platform health"""
    print("\n=== Platform Health Check Example ===")
    
    # Initialize service
    service = CrossListingService()
    
    try:
        print("Checking platform health...")
        
        health = service.health_check()
        
        print(f"\nOverall Health: {'HEALTHY' if health['overall_healthy'] else 'UNHEALTHY'}")
        print(f"Check Duration: {health['duration']:.2f} seconds")
        
        print(f"\nPlatform Status:")
        for platform, status in health['platforms'].items():
            health_icon = "✅" if status['healthy'] else "❌"
            response_time = f"{status['response_time']:.3f}s" if status['response_time'] else "N/A"
            
            print(f"  {health_icon} {platform}: {response_time}")
            
            if status['error']:
                print(f"    Error: {status['error']}")
        
    except Exception as e:
        print(f"Error: {e}")


def example_inventory_sync():
    """Example: Synchronize inventory"""
    print("\n=== Inventory Synchronization Example ===")
    
    # Initialize service
    service = CrossListingService()
    
    try:
        print("Synchronizing inventory across all platforms...")
        
        result = service.sync_all_listings()
        
        print(f"\nSync Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Duration: {result['duration']:.2f} seconds")
        print(f"Summary: {result['summary']}")
        
        print(f"\nPlatform Results:")
        for platform, platform_result in result['platform_results'].items():
            if platform_result.get('success', False):
                synced = platform_result.get('synced_count', 0)
                conflicts = platform_result.get('conflicts_count', 0)
                print(f"  ✅ {platform}: {synced} synced, {conflicts} conflicts")
            else:
                error = platform_result.get('error', 'Unknown error')
                print(f"  ❌ {platform}: {error}")
        
    except Exception as e:
        print(f"Error: {e}")


def example_configuration():
    """Example: Configuration management"""
    print("\n=== Configuration Example ===")
    
    config_manager = ConfigManager()
    
    try:
        print("Loading configuration...")
        
        config = config_manager.load_config()
        
        print(f"\nEnabled Platforms:")
        for platform_name, platform_config in config.get('platforms', {}).items():
            enabled = platform_config.get('enabled', False)
            status = "✅ Enabled" if enabled else "⏸️ Disabled"
            print(f"  {platform_name}: {status}")
        
        print(f"\nGlobal Settings:")
        global_config = config.get('global', {})
        print(f"  Default Currency: {global_config.get('default_currency', 'USD')}")
        print(f"  Max Photos: {global_config.get('max_photos_per_listing', 10)}")
        print(f"  Batch Size: {global_config.get('batch_size', 50)}")
        print(f"  Max Workers: {global_config.get('max_workers', 5)}")
        
        # Validate configuration
        validation = config_manager.validate_config()
        print(f"\nConfiguration Valid: {'✅ Yes' if validation['valid'] else '❌ No'}")
        
        if validation['errors']:
            print("Errors:")
            for error in validation['errors']:
                print(f"  - {error}")
        
        if validation['warnings']:
            print("Warnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
    except Exception as e:
        print(f"Error: {e}")


def example_listing_update():
    """Example: Update cross-platform listing"""
    print("\n=== Listing Update Example ===")
    
    # Initialize service
    service = CrossListingService()
    
    try:
        item_id = "supreme_hoodie_001"
        updates = {
            "price": 425.00,  # Price reduction
            "description": "Updated description with urgent sale!"
        }
        
        print(f"Updating item {item_id}...")
        print(f"New price: ${updates['price']}")
        
        result = service.update_cross_listing(item_id, updates)
        
        print(f"\nUpdate Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Duration: {result['duration']:.2f} seconds")
        
        if result['successful_platforms']:
            print(f"✅ Updated platforms: {', '.join(result['successful_platforms'])}")
        
        if result['failed_platforms']:
            print(f"❌ Failed platforms: {', '.join(result['failed_platforms'])}")
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all examples"""
    print("Streetwear Inventory Cross-Listing System")
    print("=" * 50)
    
    try:
        # Run examples
        example_configuration()
        example_platform_health()
        example_cross_listing()
        example_listing_update()
        example_inventory_sync()
        example_sales_report()
        
        print("\n" + "=" * 50)
        print("All examples completed!")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()