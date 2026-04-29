"""
Pydantic models for webhook payloads and responses

Skeleton only. Models will be expanded as webhook format is defined.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TradingViewAlert(BaseModel):
    """TradingView webhook payload model"""
    
    token: str = Field(..., description="Token symbol (e.g., ETH, SOL)")
    signal_type: str = Field(..., description="Signal type (OG, FVG, ChoCh, ADX)")
    direction: str = Field(..., description="LONG or SHORT")
    timestamp: Optional[datetime] = Field(default=None, description="Alert timestamp")
    price: Optional[float] = Field(default=None, description="Entry price suggestion")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "ETH",
                "signal_type": "OG",
                "direction": "LONG",
                "price": 2500.0,
            }
        }

class WebhookResponse(BaseModel):
    """Response model for webhook endpoint"""
    
    status: str = Field(..., description="Status: 'received', 'processed', 'error'")
    message: str = Field(..., description="Status message")
    order_id: Optional[str] = Field(default=None, description="MEXC order ID if processed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "received",
                "message": "Alert queued for processing",
                "order_id": None,
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
