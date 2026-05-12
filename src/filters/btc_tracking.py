"""
BTC tracking - RSI, volatilitet, och prisförändringar på flera timeframes.
"""

import asyncio
import time
from statistics import stdev
from src.clients.mexc import MexcClient
from src.filters.rsi import calculate_rsi


class BtcTracker:
    """Tracker för BTC RSI, volatilitet och prisförändringar."""
    
    def __init__(self, mexc_client: MexcClient):
        """
        Initialiserar BtcTracker.
        
        Args:
            mexc_client: MexcClient-instans för datahämtning
        """
        self.client = mexc_client
        self.cache = {
            'data': None,
            'timestamp': None
        }
        self.cache_ttl = 10  # sekunder
    
    def _is_cache_valid(self) -> bool:
        """Kontrollerar om cache är giltig (yngre än TTL)."""
        if self.cache['data'] is None or self.cache['timestamp'] is None:
            return False
        return time.time() - self.cache['timestamp'] < self.cache_ttl
    
    async def get_context(self) -> dict:
        """
        Hämtar BTC-kontext: RSI, volatilitet, prisförändringar.
        
        Returns:
            Dict med:
            - rsi_1m, rsi_5m, rsi_15m (float eller None)
            - change_1m, change_5m, change_15m (float eller None)
            - volatility_1m (float eller None)
            - timestamp (int)
        """
        # Returnera cached data om giltig
        if self._is_cache_valid():
            return self.cache['data']
        
        # Hämta data från MEXC async parallellt
        klines_1m, klines_5m, klines_15m = await asyncio.gather(
            asyncio.to_thread(self.client.get_klines, 'BTC_USDT', 'Min1', 50),
            asyncio.to_thread(self.client.get_klines, 'BTC_USDT', 'Min5', 50),
            asyncio.to_thread(self.client.get_klines, 'BTC_USDT', 'Min15', 50),
        )
        
        # Extrahera closes
        closes_1m = [k['close'] for k in klines_1m] if klines_1m else []
        closes_5m = [k['close'] for k in klines_5m] if klines_5m else []
        closes_15m = [k['close'] for k in klines_15m] if klines_15m else []
        
        # Beräkna RSI för varje timeframe
        rsi_1m = calculate_rsi(closes_1m, period=14) if closes_1m else None
        rsi_5m = calculate_rsi(closes_5m, period=14) if closes_5m else None
        rsi_15m = calculate_rsi(closes_15m, period=14) if closes_15m else None
        
        # Beräkna procentuell förändring från 1-min closes
        # Mäter senaste 1/5/15 minuter
        change_1m = self._calculate_change_n_back(closes_1m, 1)
        change_5m = self._calculate_change_n_back(closes_1m, 5)
        change_15m = self._calculate_change_n_back(closes_1m, 15)
        
        # Beräkna volatilitet från 1-min candles
        volatility_1m = self._calculate_volatility(closes_1m)
        
        # Skapa resultat-dict
        result = {
            'rsi_1m': rsi_1m,
            'rsi_5m': rsi_5m,
            'rsi_15m': rsi_15m,
            'change_1m': change_1m,
            'change_5m': change_5m,
            'change_15m': change_15m,
            'volatility_1m': volatility_1m,
            'timestamp': int(time.time())
        }
        
        # Cache resultat
        self.cache = {
            'data': result,
            'timestamp': time.time()
        }
        
        return result
    
    def _calculate_change_n_back(self, closes: list[float], n: int) -> float | None:
        """
        Beräknar procentuell förändring från n candles bakåt till senaste.
        
        Args:
            closes: Lista med stängningspriser (1-min)
            n: Antal minuter bakåt (antal candles)
        
        Returns:
            Procentuell förändring, eller None om otillräcklig data
        """
        if len(closes) < n + 1:
            return None
        
        prev = closes[-n - 1]
        last = closes[-1]
        
        if prev == 0:
            return None
        
        change = ((last - prev) / prev) * 100
        return round(change, 4)
    
    def _calculate_volatility(self, closes: list[float]) -> float | None:
        """
        Beräknar volatilitet som standardavvikelse av % förändringar.
        Använder senaste 15 candles från 1-min timeframe.
        
        Args:
            closes: Lista med stängningspriser (från 1-min)
        
        Returns:
            Standardavvikelse av % förändringar, eller None om <2 datapunkter
        """
        if len(closes) < 2:
            return None
        
        # Använd senaste 15 candles om tillgängligt
        recent_closes = closes[-15:] if len(closes) >= 15 else closes
        
        # Beräkna % förändringar
        pct_changes = []
        for i in range(1, len(recent_closes)):
            prev = recent_closes[i - 1]
            curr = recent_closes[i]
            
            if prev != 0:
                pct_change = ((curr - prev) / prev) * 100
                pct_changes.append(pct_change)
        
        # Beräkna standardavvikelse
        if len(pct_changes) < 2:
            return None
        
        volatility = stdev(pct_changes)
        return round(volatility, 4)
