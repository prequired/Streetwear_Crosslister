from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass
class SaleData:
    """Standardized sale data structure across all platforms"""
    sale_id: str
    listing_id: str
    buyer_info: Dict[str, Any]
    sale_date: datetime
    gross_amount: float
    fees: float
    net_amount: float
    platform: str
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'sale_id': self.sale_id,
            'listing_id': self.listing_id,
            'buyer_info': self.buyer_info,
            'sale_date': self.sale_date.isoformat() if self.sale_date else None,
            'gross_amount': self.gross_amount,
            'fees': self.fees,
            'net_amount': self.net_amount,
            'platform': self.platform,
            'extra': self.extra
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SaleData':
        """Create from dictionary"""
        data = data.copy()
        if 'sale_date' in data and isinstance(data['sale_date'], str):
            data['sale_date'] = datetime.fromisoformat(data['sale_date'])
        
        return cls(**data)
    
    def validate(self) -> bool:
        """Validate required fields and data types"""
        if not self.sale_id or not self.listing_id or not self.platform:
            return False
        if self.gross_amount <= 0:
            return False
        if self.fees < 0 or self.net_amount < 0:
            return False
        return True
    
    def calculate_profit_margin(self) -> float:
        """Calculate profit margin percentage"""
        if self.gross_amount <= 0:
            return 0.0
        return (self.net_amount / self.gross_amount) * 100