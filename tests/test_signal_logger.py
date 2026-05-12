import sys
import tempfile
import os
sys.path.insert(0, '.')

from src.services.signal_logger import SignalLogger


def main():
    # Skapa temporär katalog för test-logs
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Temporär log-katalog: {tmpdir}")
        logger = SignalLogger(log_dir=tmpdir)
        
        print()
        print("Test 1: Normalt signal-resultat (alla värden presente)")
        result1 = {
            'evaluated_at': 1715500800,
            'alert_id': 'eth_og_long_001',
            'symbol': 'ETHUSDT.P',
            'signal_type': 'OG',
            'direction': 'long',
            'price': 2500.5,
            'passed': True,
            'skip_reason': None,
            'token_rsi_1m': 45.2,
            'token_rsi_5m': 42.8,
            'token_rsi_15m': 40.1,
            'btc_context': {
                'rsi_1m': 50.0,
                'rsi_5m': 48.5,
                'rsi_15m': 49.2,
                'change_1m': 0.05,
                'change_5m': 0.12,
                'change_15m': 0.25,
                'volatility_1m': 0.0234
            }
        }
        logger.log_signal(result1)
        print(" Signalerad loggad")
        
        print()
        print("Test 2: Signal med 0.0-värden (kritiskt test)")
        result2 = {
            'evaluated_at': 1715500860,
            'alert_id': 'sol_og_short_002',
            'symbol': 'SOLUSDT.P',
            'signal_type': 'OG',
            'direction': 'short',
            'price': 150.0,
            'passed': False,
            'skip_reason': 'btc_decline_too_steep',
            'token_rsi_1m': 25.0,  # Låg men giltig
            'token_rsi_5m': 30.5,
            'token_rsi_15m': 35.2,
            'btc_context': {
                'rsi_1m': 40.0,
                'rsi_5m': 42.0,
                'rsi_15m': 43.0,
                'change_1m': 0.0,  # KRITISKT: ska loggas som 0.0, inte tom
                'change_5m': 0.0,  # KRITISKT: ska loggas som 0.0, inte tom
                'change_15m': -2.5,
                'volatility_1m': 0.0  # KRITISKT: ska loggas som 0.0, inte tom
            }
        }
        logger.log_signal(result2)
        print(" Signal med 0.0-värden loggad")
        
        print()
        print("Test 3: Signal med None-värden (saknad data)")
        result3 = {
            'evaluated_at': 1715500920,
            'alert_id': 'tao_og_long_003',
            'symbol': 'TAOUSDT.P',
            'signal_type': 'OG',
            'direction': 'long',
            'price': 400.75,
            'passed': False,
            'skip_reason': 'missing_data_token_rsi_1m',
            'token_rsi_1m': None,  # Saknad data
            'token_rsi_5m': None,  # Saknad data
            'token_rsi_15m': None,  # Saknad data
            'btc_context': {
                'rsi_1m': None,
                'rsi_5m': None,
                'rsi_15m': None,
                'change_1m': None,
                'change_5m': None,
                'change_15m': None,
                'volatility_1m': None
            }
        }
        logger.log_signal(result3)
        print(" Signal med None-värden loggad")
        
        # Läs och visa CSV-innehål
        print()
        print("CSV-innehål:")
        csv_path = os.path.join(tmpdir, 'signals.csv')
        with open(csv_path, 'r') as f:
            csv_content = f.read()
            print(csv_content)
        
        # Läs och visa första JSONL-raden
        print()
        print("JSONL - första raden:")
        jsonl_path = os.path.join(tmpdir, 'signals.jsonl')
        with open(jsonl_path, 'r') as f:
            first_line = f.readline()
            print(first_line[:200] + "..." if len(first_line) > 200 else first_line)
        
        # Sanity checks
        print()
        print("Sanity checks:")
        
        # Check 1: Rätt antal rader i CSV
        with open(csv_path, 'r') as f:
            lines = f.readlines()
        expected_rows = 4  # 1 header + 3 data
        assert len(lines) == expected_rows, f"CSV har {len(lines)} rader, förväntat {expected_rows}"
        print(f" CSV: {len(lines)} rader (1 header + 3 data) ✓")
        
        # Check 2: 0.0-värden är bevarade (inte tomma)
        csv_lines = [l.strip() for l in lines]
        test2_line = csv_lines[2]  # Test 2-raden (index 1 är data, index 2 är test 2)
        # Kolumn: change_1m, change_5m, change_15m, volatility_1m (nästan sist)
        # Läs CSV-fälten för test 2
        fields = test2_line.split(',')
        # change_1m är fält ~15, change_5m ~16, change_15m ~17, volatility_1m ~18
        # Räkna från början: evaluated_at_iso, evaluated_at, alert_id, symbol, signal_type,
        # direction, price, passed, skip_reason, token_rsi_1m, token_rsi_5m, token_rsi_15m,
        # btc_rsi_1m, btc_rsi_5m, btc_rsi_15m, btc_change_1m (index 15), change_5m (16), change_15m (17), volatility (18)
        btc_change_1m = fields[15] if len(fields) > 15 else ''
        btc_change_5m = fields[16] if len(fields) > 16 else ''
        volatility = fields[18] if len(fields) > 18 else ''
        
        assert btc_change_1m == '0.0', f"btc_change_1m är '{btc_change_1m}', förväntad '0.0'"
        assert btc_change_5m == '0.0', f"btc_change_5m är '{btc_change_5m}', förväntad '0.0'"
        assert volatility == '0.0', f"volatility_1m är '{volatility}', förväntad '0.0'"
        print(" 0.0-värden bevarade i CSV (inte tomma) ✓")
        
        # Check 3: None-värden är tomma (inte null eller None)
        test3_line = csv_lines[3]
        fields3 = test3_line.split(',')
        token_rsi_1m = fields3[9] if len(fields3) > 9 else ''
        assert token_rsi_1m == '', f"token_rsi_1m för None-test är '{token_rsi_1m}', förväntad tom"
        print(" None-värden blir tomma strängar i CSV ✓")
        
        print()
        print("Alla sanity checks passerade!")


if __name__ == "__main__":
    main()
