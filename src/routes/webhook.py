"""
Webhook route handlers

Receives TradingView alerts and processes them.
Skeleton only — no actual trading logic yet.
"""

from fastapi import APIRouter, HTTPException, status
from src.config import settings
from src.models import TradingViewAlert, WebhookResponse

webhook_router = APIRouter()

@webhook_router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(alert: TradingViewAlert):
    """
    Handle incoming TradingView webhook alert
    
    Auth token is validated from payload.auth_token, not headers.
    Modes: 'trade' = execute, 'context' = log only
    """
    
    # Validate auth token from payload
    if not alert.auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing auth_token in payload"
        )
    
    if alert.auth_token != settings.AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth_token"
        )
    
    # Handle mode
    if alert.mode == "trade":
        # TODO: Apply filters (RSI, BTC tracking, etc.)
        # TODO: Evaluate signal
        # TODO: Place order on MEXC if filters pass
        mode_action = "TRADE: Signal queued for execution"
    elif alert.mode == "context":
        # Context mode: logging only (e.g., BTC tracking)
        mode_action = "CONTEXT: Signal logged for monitoring"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {alert.mode}. Must be 'trade' or 'context'"
        )
    
    return WebhookResponse(
        status="received",
        message=f"Alert {alert.alert_id} ({alert.signal_type} {alert.direction} on {alert.symbol}). {mode_action}",
        order_id=None,
    )

@webhook_router.get("/webhook/status")
async def webhook_status():
    """Check webhook receiver status"""
    return {
        "status": "operational",
        "receiver": "SMOG Bot",
        "version": "0.1.0",
    }
