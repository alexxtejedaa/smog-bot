"""
Pydantic models for webhook payloads and responses

Skeleton only. Models will be expanded as webhook format is defined.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class TradingViewAlert(BaseModel):
    """TradingView webhook payload model — matches actual alert schema"""
    
    auth_token: str = Field(..., description="Authentication token from payload")
    mode: Literal["trade", "context"] = Field(..., description="'trade' for execution, 'context' for logging only")
    signal_type: Literal["OG", "FVG", "ChoCh", "ADX"] = Field(..., description="Signal type")
    direction: Literal["long", "short"] = Field(..., description="'long' or 'short' (lowercase)")
    symbol: str = Field(..., description="Trading symbol (e.g., 'ETHUSDT.P')")
    timeframe: str = Field(..., description="Timeframe (e.g., '1', '5', '15')")
    price: float = Field(..., description="Entry price")
    timestamp: datetime = Field(..., description="ISO format timestamp (auto-parsed by Pydantic)")
    alert_id: str = Field(..., description="Alert identifier (e.g., 'eth_og_short')")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "auth_token": "secret_token_here",
                "mode": "trade",
                "signal_type": "OG",
                "direction": "long",
                "symbol": "ETHUSDT.P",
                "timeframe": "1",
                "price": 2500.0,
                "timestamp": "2026-04-29T13:00:00Z",
                "alert_id": "eth_og_long",
            }
        }
    }

class WebhookResponse(BaseModel):
    """Response model for webhook endpoint"""
    
    status: str = Field(..., description="Status: 'received', 'processed', 'error'")
    message: str = Field(..., description="Status message")
    order_id: Optional[str] = Field(default=None, description="MEXC order ID if processed")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "received",
                "message": "Alert queued for processing",
                "order_id": None,
            }
        }
    }

class FilterResult(BaseModel):
    """Filter evaluation result"""
    
    passed: bool = Field(..., description="Did alert pass all filters?")
    rsi_value: Optional[float] = Field(default=None)
    rsi_passed: Optional[bool] = Field(default=None)
    btc_change_1m: Optional[float] = Field(default=None)
    btc_change_5m: Optional[float] = Field(default=None)
    btc_change_15m: Optional[float] = Field(default=None)
    filters_status: Optional[dict] = Field(default=None)
