"""
Webhook route handlers

Receives TradingView alerts and processes them.
Skeleton only — no actual trading logic yet.
"""

from fastapi import APIRouter, Header, HTTPException, status
from src.config import settings
from src.models import TradingViewAlert, WebhookResponse

webhook_router = APIRouter()

@webhook_router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(
    alert: TradingViewAlert,
    authorization: str = Header(None),
):
    """
    Handle incoming TradingView webhook alert
    
    Expected header: Authorization: Bearer {AUTH_TOKEN}
    """
    
    # Validate auth token
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    expected_token = f"Bearer {settings.AUTH_TOKEN}"
    if authorization != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token"
        )
    
    # Placeholder: log the alert
    # TODO: Apply filters (RSI, BTC tracking, etc.)
    # TODO: Evaluate signal
    # TODO: Place order on MEXC if filters pass
    
    return WebhookResponse(
        status="received",
        message=f"Alert for {alert.token} {alert.direction} ({alert.signal_type}) received and queued",
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
