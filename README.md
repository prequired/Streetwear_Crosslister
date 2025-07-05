# Streetwear Inventory Cross-Listing System

A comprehensive CLI application for managing streetwear inventory across multiple marketplace platforms including Mercari, Vinted, and Facebook Marketplace.

## Features

- **Cross-Platform Listing**: Create listings simultaneously across multiple platforms
- **Inventory Synchronization**: Keep your inventory in sync across all platforms
- **Sales Analytics**: Generate comprehensive sales reports with profit analysis
- **Platform Management**: Monitor platform health and API status
- **Automated Operations**: Bulk operations and scheduled synchronization

## Supported Platforms

- ✅ **Mercari** - Full integration with OAuth authentication
- 🚧 **Vinted** - In development (OAuth 2.0 with token refresh)
- 🚧 **Facebook Marketplace** - In development (Graph API integration)

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Platform API credentials (see Configuration section)

### Installation

1. Clone or download the project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```

4. Configure your API credentials in `.env`

### Basic Usage

1. **Test Configuration**:
   ```bash
   python -m src config-test
   ```

2. **Check Platform Status**:
   ```bash
   python -m src platform-status
   ```

3. **Create a Cross-Platform Listing**:
   ```bash
   python -m src cross list item_001 \
     --platforms mercari \
     --title "Supreme Box Logo Hoodie" \
     --description "Authentic Supreme hoodie in excellent condition" \
     --price 250.00 \
     --condition "Excellent" \
     --brand "Supreme" \
     --size "L" \
     --category "Clothing"
   ```

4. **Generate Sales Report**:
   ```bash
   python -m src sales-report --days 30
   ```

## Configuration

### Environment Variables

Create a `.env` file with your API credentials:

```bash
# Mercari Configuration
MERCARI_API_KEY=your_api_key
MERCARI_SECRET=your_secret
MERCARI_ACCESS_TOKEN=your_access_token
MERCARI_SANDBOX=true

# Vinted Configuration (when available)
VINTED_CLIENT_ID=your_client_id
VINTED_CLIENT_SECRET=your_client_secret
VINTED_ACCESS_TOKEN=your_access_token
VINTED_REFRESH_TOKEN=your_refresh_token

# Facebook Marketplace Configuration (when available)
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_ACCESS_TOKEN=your_access_token
FACEBOOK_PAGE_ID=your_page_id
```

### Platform Configuration

Edit `config/platforms.yaml` to enable/disable platforms and configure settings:

```yaml
platforms:
  mercari:
    enabled: true
    sandbox: true
    rate_limit:
      requests_per_minute: 100
  
  vinted:
    enabled: false
  
  facebook_marketplace:
    enabled: false
```

## CLI Commands

### Cross-Listing Commands

- `cross list` - Create a listing across multiple platforms
- `cross update` - Update a listing across all platforms
- `cross delete` - Delete a listing from all platforms
- `cross sync` - Synchronize inventory across platforms

### Analytics Commands

- `sales-report` - Generate sales reports with filtering options
- `platform-status` - Check health status of all platforms

### Configuration Commands

- `config-test` - Validate configuration files

## API Reference

### Cross-Listing Service

```python
from src.services.cross_listing_service import CrossListingService

service = CrossListingService()

# Create cross-platform listing
result = service.create_cross_listing(listing_data, ["mercari", "vinted"])

# Update listing across platforms
result = service.update_cross_listing("item_001", {"price": 200.00})

# Generate sales report
report = service.get_sales_report()
```

### Platform Integration

```python
from src.platforms.mercari import MercariPlatform

platform = MercariPlatform(config)
platform.authenticate()
listing_id = platform.list_item(listing_data)
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_platforms/test_mercari.py

# Run with verbose output
pytest -v
```

## Development

### Project Structure

```
src/
├── platforms/          # Platform integrations
│   ├── base.py         # Base platform class
│   ├── mercari.py      # Mercari implementation
│   ├── vinted.py       # Vinted implementation (coming soon)
│   └── facebook_marketplace.py  # Facebook implementation (coming soon)
├── models/             # Data models
│   ├── listing_data.py
│   └── sale_data.py
├── services/           # Business logic
│   └── cross_listing_service.py
├── utils/              # Utilities
│   ├── config_manager.py
│   ├── logger.py
│   └── retry.py
└── cli/                # CLI interface
    └── commands.py
```

### Adding a New Platform

1. Create a new platform class inheriting from `PlatformBase`
2. Implement all abstract methods
3. Add platform configuration to `config/platforms.yaml`
4. Update the service to initialize the new platform
5. Add comprehensive tests

## Logging

The application uses structured logging with JSON format for production environments. Logs are written to:

- Console output (formatted for readability)
- `logs/cross_listing.log` (JSON format with rotation)

Log levels can be configured in `config/platforms.yaml` or via environment variables.

## Error Handling

The system includes comprehensive error handling:

- **Retry Logic**: Automatic retries for transient failures
- **Circuit Breakers**: Prevent cascading failures
- **Rate Limiting**: Respect platform API limits
- **Graceful Degradation**: Continue operation when platforms are unavailable

## Security

- API credentials are encrypted at rest
- Sensitive data is masked in logs
- HTTPS is used for all API communications
- Regular security audits are performed

## Performance

- Parallel processing for multi-platform operations
- Intelligent caching to reduce API calls
- Batch operations for bulk updates
- Performance monitoring and metrics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section in the documentation
2. Review existing GitHub issues
3. Create a new issue with detailed information

## Roadmap

### Phase 1: Foundation ✅
- [x] Base architecture and models
- [x] Mercari integration
- [x] CLI interface
- [x] Basic testing framework

### Phase 2: Platform Expansion 🚧
- [ ] Vinted integration
- [ ] Facebook Marketplace integration
- [ ] Enhanced error handling
- [ ] Performance optimization

### Phase 3: Advanced Features 📋
- [ ] Automated price optimization
- [ ] Inventory forecasting
- [ ] Multi-currency support
- [ ] Advanced analytics dashboard

### Phase 4: Enterprise Features 📋
- [ ] Multi-user support
- [ ] API rate limiting management
- [ ] Advanced reporting
- [ ] Integration webhooks
