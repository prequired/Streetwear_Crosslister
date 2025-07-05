import click
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

from ..services.cross_listing_service import CrossListingService
from ..models.listing_data import ListingData
from ..utils.config_manager import ConfigManager
from ..utils.logger import setup_logging


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--config', type=str, help='Path to config directory')
@click.pass_context
def inventory(ctx, debug, config):
    """Streetwear Inventory Cross-Listing CLI"""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['config_dir'] = config or 'config'
    
    # Setup logging
    log_config = {
        'level': 'DEBUG' if debug else 'INFO',
        'file': 'logs/cli.log'
    }
    ctx.obj['logger'] = setup_logging(log_config)


@inventory.group()
@click.pass_context
def cross(ctx):
    """Cross-platform listing commands"""
    pass


@cross.command('list')
@click.argument('item_id')
@click.option('--platforms', type=str, default='mercari', 
              help='Comma-separated list of platforms (mercari,vinted,facebook)')
@click.option('--title', type=str, required=True, help='Item title')
@click.option('--description', type=str, required=True, help='Item description')
@click.option('--price', type=float, required=True, help='Item price')
@click.option('--condition', type=str, required=True, 
              help='Item condition (New,Like New,Excellent,Good,Fair,Poor)')
@click.option('--size', type=str, help='Item size')
@click.option('--brand', type=str, help='Item brand')
@click.option('--category', type=str, help='Item category')
@click.option('--photos', type=str, help='Comma-separated list of photo URLs')
@click.option('--quantity', type=int, default=1, help='Quantity available')
@click.pass_context
def cross_list(ctx, item_id, platforms, title, description, price, condition, 
               size, brand, category, photos, quantity):
    """Create a listing across multiple platforms"""
    try:
        # Initialize service
        service = CrossListingService()
        
        # Parse platforms
        target_platforms = [p.strip() for p in platforms.split(',')]
        
        # Parse photos
        photo_list = []
        if photos:
            photo_list = [p.strip() for p in photos.split(',')]
        
        # Create listing data
        listing_data = ListingData(
            item_id=item_id,
            platform="",  # Will be set per platform
            platform_listing_id="",
            title=title,
            description=description,
            price=price,
            quantity=quantity,
            condition=condition,
            size=size,
            brand=brand,
            category=category,
            photos=photo_list
        )
        
        # Validate listing data
        if not listing_data.validate():
            click.echo("❌ Invalid listing data. Please check your inputs.", err=True)
            sys.exit(1)
        
        click.echo(f"🚀 Creating listing for '{title}' on platforms: {', '.join(target_platforms)}")
        
        # Create cross-listing
        result = service.create_cross_listing(listing_data, target_platforms)
        
        if result['success']:
            click.echo("✅ Cross-listing created successfully!")
            click.echo(f"📊 Duration: {result['duration']:.2f}s")
            
            if result['listing_ids']:
                click.echo("\n📋 Platform Listing IDs:")
                for platform, listing_id in result['listing_ids'].items():
                    click.echo(f"  • {platform}: {listing_id}")
            
            if result['failed_platforms']:
                click.echo(f"\n⚠️  Failed platforms: {', '.join(result['failed_platforms'])}")
        else:
            click.echo(f"❌ Cross-listing failed: {result.get('error', 'Unknown error')}", err=True)
            if result['failed_platforms']:
                click.echo(f"Failed platforms: {', '.join(result['failed_platforms'])}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cross.command('update')
@click.argument('item_id')
@click.option('--price', type=float, help='New price')
@click.option('--title', type=str, help='New title')
@click.option('--description', type=str, help='New description')
@click.option('--condition', type=str, help='New condition')
@click.option('--quantity', type=int, help='New quantity')
@click.pass_context
def cross_update(ctx, item_id, price, title, description, condition, quantity):
    """Update a listing across all platforms"""
    try:
        # Initialize service
        service = CrossListingService()
        
        # Build updates dict
        updates = {}
        if price is not None:
            updates['price'] = price
        if title:
            updates['title'] = title
        if description:
            updates['description'] = description
        if condition:
            updates['condition'] = condition
        if quantity is not None:
            updates['quantity'] = quantity
        
        if not updates:
            click.echo("❌ No updates specified. Use --help to see available options.", err=True)
            sys.exit(1)
        
        click.echo(f"🔄 Updating listing {item_id} with: {', '.join(updates.keys())}")
        
        # Update cross-listing
        result = service.update_cross_listing(item_id, updates)
        
        if result['success']:
            click.echo("✅ Cross-listing updated successfully!")
            click.echo(f"📊 Duration: {result['duration']:.2f}s")
            
            if result['successful_platforms']:
                click.echo(f"✅ Updated platforms: {', '.join(result['successful_platforms'])}")
            
            if result['failed_platforms']:
                click.echo(f"⚠️  Failed platforms: {', '.join(result['failed_platforms'])}")
        else:
            click.echo(f"❌ Update failed: {result.get('error', 'Unknown error')}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cross.command('delete')
@click.argument('item_id')
@click.confirmation_option(prompt='Are you sure you want to delete this listing from all platforms?')
@click.pass_context
def cross_delete(ctx, item_id):
    """Delete a listing from all platforms"""
    try:
        # Initialize service
        service = CrossListingService()
        
        click.echo(f"🗑️  Deleting listing {item_id} from all platforms...")
        
        # Delete cross-listing
        result = service.delete_cross_listing(item_id)
        
        if result['success']:
            click.echo("✅ Cross-listing deleted successfully!")
            click.echo(f"📊 Duration: {result['duration']:.2f}s")
            
            if result['successful_platforms']:
                click.echo(f"✅ Deleted from platforms: {', '.join(result['successful_platforms'])}")
            
            if result['failed_platforms']:
                click.echo(f"⚠️  Failed to delete from: {', '.join(result['failed_platforms'])}")
        else:
            click.echo(f"❌ Deletion failed: {result.get('error', 'Unknown error')}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cross.command('sync')
@click.pass_context
def cross_sync(ctx):
    """Synchronize inventory across all platforms"""
    try:
        # Initialize service
        service = CrossListingService()
        
        click.echo("🔄 Synchronizing inventory across all platforms...")
        
        # Sync all listings
        result = service.sync_all_listings()
        
        if result['success']:
            click.echo("✅ Synchronization completed!")
            click.echo(f"📊 Duration: {result['duration']:.2f}s")
            click.echo(f"📝 {result['summary']}")
            
            # Show platform results
            if result['platform_results']:
                click.echo("\n📋 Platform Results:")
                for platform, platform_result in result['platform_results'].items():
                    if platform_result.get('success', False):
                        synced = platform_result.get('synced_count', 0)
                        conflicts = platform_result.get('conflicts_count', 0)
                        click.echo(f"  • {platform}: {synced} synced, {conflicts} conflicts")
                    else:
                        error = platform_result.get('error', 'Unknown error')
                        click.echo(f"  • {platform}: ❌ {error}")
        else:
            click.echo("❌ Synchronization failed", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@inventory.command('sales-report')
@click.option('--platform', type=str, help='Specific platform (mercari,vinted,facebook)')
@click.option('--since', type=str, help='Start date (YYYY-MM-DD)')
@click.option('--until', type=str, help='End date (YYYY-MM-DD)')
@click.option('--days', type=int, default=30, help='Number of days back from today')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def sales_report(ctx, platform, since, until, days, output_format):
    """Generate sales report"""
    try:
        # Initialize service
        service = CrossListingService()
        
        # Parse date range
        if since or until:
            if since:
                start_date = datetime.strptime(since, '%Y-%m-%d')
            else:
                start_date = datetime.now() - timedelta(days=30)
            
            if until:
                end_date = datetime.strptime(until, '%Y-%m-%d')
            else:
                end_date = datetime.now()
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        
        date_range = (start_date, end_date)
        
        click.echo(f"📊 Generating sales report from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Generate report
        result = service.get_sales_report(date_range)
        
        if output_format == 'json':
            click.echo(json.dumps(result, indent=2))
        else:
            # Display table format
            summary = result['summary']
            click.echo("\n📈 Sales Summary:")
            click.echo(f"  Total Sales: {summary['total_sales']}")
            click.echo(f"  Gross Revenue: ${summary['total_gross']:.2f}")
            click.echo(f"  Total Fees: ${summary['total_fees']:.2f}")
            click.echo(f"  Net Revenue: ${summary['total_net']:.2f}")
            click.echo(f"  Average Sale: ${summary['average_sale']:.2f}")
            click.echo(f"  Profit Margin: {summary['profit_margin']:.1f}%")
            
            # Platform breakdown
            if result['platform_breakdown']:
                click.echo("\n🏪 Platform Breakdown:")
                for platform_name, stats in result['platform_breakdown'].items():
                    click.echo(f"  {platform_name}:")
                    click.echo(f"    Sales: {stats['sales_count']}")
                    click.echo(f"    Gross: ${stats['gross_amount']:.2f}")
                    click.echo(f"    Net: ${stats['net_amount']:.2f}")
            
            click.echo(f"\n⏱️  Report generated in {result['duration']:.2f}s")
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@inventory.command('platform-status')
@click.pass_context
def platform_status(ctx):
    """Check status of all platforms"""
    try:
        # Initialize service
        service = CrossListingService()
        
        click.echo("🔍 Checking platform status...")
        
        # Perform health check
        result = service.health_check()
        
        click.echo(f"\n🏥 Overall Health: {'✅ Healthy' if result['overall_healthy'] else '❌ Unhealthy'}")
        click.echo(f"⏱️  Check Duration: {result['duration']:.2f}s")
        click.echo(f"🕐 Timestamp: {result['timestamp']}")
        
        # Platform details
        click.echo("\n🏪 Platform Status:")
        for platform_name, status in result['platforms'].items():
            health_icon = "✅" if status['healthy'] else "❌"
            response_time = f"{status['response_time']:.3f}s" if status['response_time'] else "N/A"
            
            click.echo(f"  {health_icon} {platform_name}: {response_time}")
            
            if status['error']:
                click.echo(f"    Error: {status['error']}")
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@inventory.command('config-test')
@click.pass_context
def config_test(ctx):
    """Test configuration validity"""
    try:
        config_manager = ConfigManager(ctx.obj['config_dir'])
        
        click.echo("🔧 Testing configuration...")
        
        # Validate config
        result = config_manager.validate_config()
        
        if result['valid']:
            click.echo("✅ Configuration is valid!")
        else:
            click.echo("❌ Configuration has errors:")
            for error in result['errors']:
                click.echo(f"  • {error}")
        
        if result['warnings']:
            click.echo("\n⚠️  Warnings:")
            for warning in result['warnings']:
                click.echo(f"  • {warning}")
        
        # Test platform configs
        config = config_manager.load_config()
        click.echo("\n🏪 Platform Configuration:")
        
        for platform_name, platform_config in config.get('platforms', {}).items():
            enabled = platform_config.get('enabled', False)
            status_icon = "✅" if enabled else "⏸️"
            click.echo(f"  {status_icon} {platform_name}: {'Enabled' if enabled else 'Disabled'}")
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    inventory()