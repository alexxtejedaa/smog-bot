"""
Webhook route handlers

Receives TradingView alerts, evaluates them through filters,
and logs results. Integration point for aggregator + signal_logger.
"""

import asyncio
import logging
import time
from fastapi import APIRouter, HTTPException, status
from src.config import settings
from src.models import TradingViewAlert, WebhookResponse
from src.clients.mexc import MexcClient
from src.filters.aggregator import FilterAggregator
from src.services.signal_logger import SignalLogger

log = logging.getLogger("webhook")

webhook_router = APIRouter()

# Module-level singletons (lazy initialization)
_mexc_client: MexcClient | None = None
_aggregator: FilterAggregator | None = None
_signal_logger: SignalLogger | None = None


def _init_singletons():
    """
    Lazy initialization of module-level singletons.
    Called once on first webhook request.
    
    Raises:
        ValueError: If MEXC credentials are missing
    """
    global _mexc_client, _aggregator, _signal_logger
    
    if _mexc_client is not None:
        return  # Already initialized
    
    # Validate MEXC credentials
    if not settings.MEXC_API_KEY or not settings.MEXC_API_SECRET:
        raise ValueError(
            "MEXC credentials missing. Set MEXC_API_KEY and MEXC_API_SECRET in .env"
        )
    
    # Create singletons
    _mexc_client = MexcClient(
        api_key=settings.MEXC_API_KEY,
        api_secret=settings.MEXC_API_SECRET,
    )
    _aggregator = FilterAggregator(_mexc_client)
    
    # Log directory: use config LOG_DIR
    log_dir = settings.LOG_DIR
    _signal_logger = SignalLogger(log_dir=log_dir)
    
    log.info("Webhook singletons initialized (MEXC, Aggregator, Logger)")


@webhook_router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(alert: TradingViewAlert):
    """
    Handle incoming TradingView webhook alert.
    
    Flow:
    1. Validate auth token
    2. Initialize singletons (lazy)
    3. If mode="trade": evaluate through aggregator, log result
    4. If mode="context": log only (BTC tracking, etc.)
    5. Return response based on filter result
    
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
    
    # Initialize singletons on first request
    try:
        _init_singletons()
    except ValueError as e:
        log.error(f"Initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
        )
    
    # Handle mode: 'trade' or 'context'
    if alert.mode == "trade":
        # Evaluate signal through aggregator
        try:
            evaluation_result = await _aggregator.evaluate(alert)
        except Exception as e:
            log.error(f"Aggregator evaluation failed for {alert.alert_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Filter evaluation failed: {str(e)}"
            )
        
        # Log result (async, but don't block response on error)
        try:
            _signal_logger.log_signal(evaluation_result)
        except Exception as e:
            log.error(f"Signal logging failed for {alert.alert_id}: {e}")
            # Don't raise — logging failure shouldn't block response
        
        # Build response based on filter result
        if evaluation_result['passed']:
            return WebhookResponse(
                status="received",
                message=f"Signal {alert.alert_id} passerade filter",
                order_id=None,
            )
        else:
            skip_reason = evaluation_result.get('skip_reason', 'unknown')
            return WebhookResponse(
                status="filtered",
                message=f"Signal {alert.alert_id} filtrerad: {skip_reason}",
                order_id=None,
            )
    
    elif alert.mode == "context":
        # TODO: Context-mode är skelett. När BTC-tracking-alerts läggs
        # till i TradingView, ska detta block hämta verklig BTC-data
        # via aggregator istället för att logga None-värden.
        
        # Context mode: logging only (e.g., BTC tracking alerts)
        # Create minimal result dict for logging
        context_result = {
            'evaluated_at': int(time.time()),
            'alert_id': alert.alert_id,
            'symbol': alert.symbol,
            'signal_type': alert.signal_type,
            'direction': alert.direction,
            'price': alert.price,
            'passed': None,  # Not applicable for context mode
            'skip_reason': 'context_mode_only',
            'token_rsi_1m': None,
            'token_rsi_5m': None,
            'token_rsi_15m': None,
            'btc_context': {
                'rsi_1m': None,
                'rsi_5m': None,
                'rsi_15m': None,
                'change_1m': None,
                'change_5m': None,
                'change_15m': None,
                'volatility_1m': None,
            }
        }
        
        try:
            _signal_logger.log_signal(context_result)
        except Exception as e:
            log.error(f"Context logging failed for {alert.alert_id}: {e}")
            # Don't raise
        
        return WebhookResponse(
            status="logged",
            message=f"Context alert {alert.alert_id} logged (BTC monitoring)",
            order_id=None,
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {alert.mode}. Must be 'trade' or 'context'"
        )


@webhook_router.get("/webhook/status")
async def webhook_status():
    """Check webhook receiver status"""
    return {
        "status": "operational",
        "receiver": "SMOG Bot",
        "version": "0.2.0",
    }
