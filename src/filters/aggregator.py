"""
FilterAggregator - kombinerar alla filter och returnerar ett godkänd/avslaget beslut.
"""

import asyncio
import time
from src.clients.mexc import MexcClient
from src.filters.rsi import calculate_rsi
from src.filters.btc_tracking import BtcTracker
from src.utils.symbol_mapper import tradingview_to_mexc
from src.models import TradingViewAlert


class FilterAggregator:
    """Aggregerar alla filter och fattar beslut om trade-signal."""
    
    def __init__(self, mexc_client: MexcClient):
        """
        Initialiserar FilterAggregator.
        
        Args:
            mexc_client: MexcClient-instans för datahämtning
        """
        self.client = mexc_client
        self.btc_tracker = BtcTracker(mexc_client)
        
        # TODO: Flytta dessa till config.py när config-system är på plats
        self.thresholds = {
            'rsi_1m_long_max': 75,      # Skip long om RSI > detta
            'rsi_1m_short_min': 25,     # Skip short om RSI < detta
            'btc_change_15m_long_min': -1.5,  # Skip long om BTC förändring < detta
            'btc_change_15m_short_max': 1.5,  # Skip short om BTC förändring > detta
        }
    
    async def evaluate(self, alert: TradingViewAlert) -> dict:
        """
        Evaluerar en inkommande TradingView-signal mot alla filter.
        
        Args:
            alert: TradingViewAlert med symbol, signal_type, direction, alert_id
        
        Returns:
            Dict med:
            - passed: bool (passerade alla filter?)
            - skip_reason: str | None (varför filtrerad, om applicable)
            - token_rsi_1m, token_rsi_5m, token_rsi_15m: float | None
            - btc_context: dict (BTC RSI, change, volatility)
            - symbol: str (original TradingView-format)
            - signal_type: str (OG, FVG, etc)
            - direction: str (long/short)
            - price: float
            - alert_id: str
            - evaluated_at: int (unix timestamp)
        """
        # Konvertera symbol från TradingView-format till MEXC-format
        mexc_symbol = tradingview_to_mexc(alert.symbol)
        
        # Hämta data parallellt: token klines + BTC context
        klines_1m, klines_5m, klines_15m, btc_context = await asyncio.gather(
            asyncio.to_thread(self.client.get_klines, mexc_symbol, 'Min1', 50),
            asyncio.to_thread(self.client.get_klines, mexc_symbol, 'Min5', 50),
            asyncio.to_thread(self.client.get_klines, mexc_symbol, 'Min15', 50),
            self.btc_tracker.get_context(),
        )
        
        # Extrahera closes från token klines
        closes_1m = [k['close'] for k in klines_1m] if klines_1m else []
        closes_5m = [k['close'] for k in klines_5m] if klines_5m else []
        closes_15m = [k['close'] for k in klines_15m] if klines_15m else []
        
        # Beräkna RSI för varje timeframe
        token_rsi_1m = calculate_rsi(closes_1m, period=14) if closes_1m else None
        token_rsi_5m = calculate_rsi(closes_5m, period=14) if closes_5m else None
        token_rsi_15m = calculate_rsi(closes_15m, period=14) if closes_15m else None
        
        # Skapa resultat-dict
        result = {
            'passed': False,
            'skip_reason': None,
            'token_rsi_1m': token_rsi_1m,
            'token_rsi_5m': token_rsi_5m,
            'token_rsi_15m': token_rsi_15m,
            'btc_context': btc_context,
            'symbol': alert.symbol,
            'signal_type': alert.signal_type,
            'direction': alert.direction,
            'price': alert.price,
            'alert_id': alert.alert_id,
            'evaluated_at': int(time.time())
        }
        
        # Kontroll 1: Obligatorisk data
        if token_rsi_1m is None:
            result['skip_reason'] = 'missing_data_token_rsi_1m'
            return result
        
        # Kontroll 2: BTC context måste finnas
        if not btc_context or btc_context.get('change_15m') is None:
            result['skip_reason'] = 'missing_data_btc_context'
            return result
        
        # Hämta värden för tröskelvärde-kontroll
        btc_change_15m = btc_context['change_15m']
        direction = alert.direction
        
        # Kontroll 3: Applicera signal-specifika filter
        if direction == 'long':
            # Long: skip om token_rsi_1m > 75 (överköpt)
            if token_rsi_1m > self.thresholds['rsi_1m_long_max']:
                result['skip_reason'] = 'token_rsi_1m_overbought'
                return result
            
            # Long: skip om BTC har fallit för mycket (negativ trend)
            if btc_change_15m < self.thresholds['btc_change_15m_long_min']:
                result['skip_reason'] = 'btc_decline_too_steep'
                return result
        
        elif direction == 'short':
            # Short: skip om token_rsi_1m < 25 (översålt)
            if token_rsi_1m < self.thresholds['rsi_1m_short_min']:
                result['skip_reason'] = 'token_rsi_1m_oversold'
                return result
            
            # Short: skip om BTC har stigit för mycket (positiv trend)
            if btc_change_15m > self.thresholds['btc_change_15m_short_max']:
                result['skip_reason'] = 'btc_rally_too_strong'
                return result
        
        else:
            # Okänd direction-typ
            result['skip_reason'] = f'unknown_direction_type: {direction}'
            return result
        
        # Alla filter passerade
        result['passed'] = True
        result['skip_reason'] = None
        return result
