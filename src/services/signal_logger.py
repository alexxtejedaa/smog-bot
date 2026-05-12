"""
SignalLogger - loggar inkommande signaler och evaluation-resultat.

Två utgångar:
- signals.csv: för snabb analys (med CSV-escaping)
- signals.jsonl: fullständig loggning med all kontext
"""

import os
import csv
import json
import threading
from datetime import datetime


class SignalLogger:
    """Logger för trade-signaler och filter-evaluering."""
    
    # CSV-kolumner i denna exakta ordning
    CSV_HEADERS = [
        'evaluated_at_iso', 'evaluated_at', 'alert_id', 'symbol', 'signal_type', 'direction', 'price',
        'passed', 'skip_reason',
        'token_rsi_1m', 'token_rsi_5m', 'token_rsi_15m',
        'btc_rsi_1m', 'btc_rsi_5m', 'btc_rsi_15m',
        'btc_change_1m', 'btc_change_5m', 'btc_change_15m',
        'btc_volatility_1m'
    ]
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialiserar SignalLogger.
        
        Args:
            log_dir: Katalog för loggfiler (skapas om den inte finns)
        """
        self.log_dir = log_dir
        self.csv_path = os.path.join(log_dir, 'signals.csv')
        self.jsonl_path = os.path.join(log_dir, 'signals.jsonl')
        self._lock = threading.Lock()
        
        # Skapa log-katalog om den inte finns
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialisera CSV-fil med headers om den är ny
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
                writer.writeheader()
        
        # Initialisera JSONL-fil (tom om ny)
        if not os.path.exists(self.jsonl_path):
            open(self.jsonl_path, 'a').close()
    
    def _none_to_empty(self, value):
        """
        Konvertera None till tom sträng, behåll alla andra värden (inklusive 0 och 0.0).
        """
        return value if value is not None else ''
    
    def log_signal(self, evaluation_result: dict) -> None:
        """
        Loggar en signal-evaluation till CSV och JSONL.
        
        Args:
            evaluation_result: Dict från aggregator.evaluate()
                Innehåller: passed, skip_reason, token_rsi_1m/5m/15m,
                btc_context (med rsi_1m/5m/15m, change_1m/5m/15m, volatility_1m),
                symbol, signal_type, direction, price, alert_id, evaluated_at
        """
        with self._lock:
            # Logg till CSV
            self._log_csv(evaluation_result)
            # Logg till JSONL
            self._log_jsonl(evaluation_result)
    
    def _log_csv(self, result: dict) -> None:
        """Loggar evaluation-resultat som CSV-rad med säker escaping."""
        btc_ctx = result.get('btc_context', {})
        evaluated_at_unix = result.get('evaluated_at')
        
        # Konvertera unix-timestamp till ISO-formaterad datetime-sträng
        evaluated_at_iso = ''
        if evaluated_at_unix is not None:
            try:
                dt = datetime.utcfromtimestamp(evaluated_at_unix)
                evaluated_at_iso = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except (ValueError, TypeError):
                evaluated_at_iso = ''
        
        # Konvertera booleaner till "1"/"0" för CSV
        passed = '1' if result.get('passed') else '0'
        
        # Mappa resultat-fält till CSV-kolumner
        # Numeriska fält: använd explicit None-check (inte "or ''" som förlorar 0-värden)
        # Strängar: kan behålla "or ''" eftersom tom sträng = None för dem
        row_data = {
            'evaluated_at_iso': evaluated_at_iso,
            'evaluated_at': self._none_to_empty(evaluated_at_unix),
            'alert_id': result.get('alert_id') or '',
            'symbol': result.get('symbol') or '',
            'signal_type': result.get('signal_type') or '',
            'direction': result.get('direction') or '',
            'price': self._none_to_empty(result.get('price')),
            'passed': passed,
            'skip_reason': result.get('skip_reason') or '',
            'token_rsi_1m': self._none_to_empty(result.get('token_rsi_1m')),
            'token_rsi_5m': self._none_to_empty(result.get('token_rsi_5m')),
            'token_rsi_15m': self._none_to_empty(result.get('token_rsi_15m')),
            'btc_rsi_1m': self._none_to_empty(btc_ctx.get('rsi_1m')),
            'btc_rsi_5m': self._none_to_empty(btc_ctx.get('rsi_5m')),
            'btc_rsi_15m': self._none_to_empty(btc_ctx.get('rsi_15m')),
            'btc_change_1m': self._none_to_empty(btc_ctx.get('change_1m')),
            'btc_change_5m': self._none_to_empty(btc_ctx.get('change_5m')),
            'btc_change_15m': self._none_to_empty(btc_ctx.get('change_15m')),
            'btc_volatility_1m': self._none_to_empty(btc_ctx.get('volatility_1m')),
        }
        
        # Skriv rad till CSV med säker escaping
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
            writer.writerow(row_data)
    
    def _log_jsonl(self, result: dict) -> None:
        """Loggar evaluation-resultat som JSON-rad med explicit datetime-hantering."""
        def _serialize(obj):
            """Serialisera objekt som inte är JSON-kompatibla."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        # Konvertera evaluation-resultat till JSON
        json_line = json.dumps(result, default=_serialize)
        
        # Skriv rad till JSONL
        with open(self.jsonl_path, 'a') as f:
            f.write(json_line + '\n')
