from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class ListingData:
    """Standardized listing data structure across all platforms"""
    item_id: str
    platform: str
    platform_listing_id: str
    title: str
    description: str
    price: float
    quantity: int
    condition: str
    size: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    photos: List[str] = field(default_factory=list)
    url: Optional[str] = None
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'item_id': self.item_id,
            'platform': self.platform,
            'platform_listing_id': self.platform_listing_id,
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'quantity': self.quantity,
            'condition': self.condition,
            'size': self.size,
            'brand': self.brand,
            'category': self.category,
            'photos': self.photos,
            'url': self.url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'extra': self.extra
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ListingData':
        """Create from dictionary"""
        data = data.copy()
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return cls(**data)
    
    def validate(self) -> bool:
        """Validate required fields and data types"""
        if not self.item_id or not self.title:
            return False
        if self.price <= 0 or self.quantity <= 0:
            return False
        if self.condition not in ['New', 'Like New', 'Excellent', 'Good', 'Fair', 'Poor']:
            return False
        return True