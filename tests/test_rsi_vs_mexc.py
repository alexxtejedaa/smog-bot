import sys
sys.path.insert(0, '.')
from src.clients.mexc import MexcClient
from src.filters.rsi import calculate_rsi

# Skapa client utan auth (public endpoints räcker)
client = MexcClient(api_key='', api_secret='')

# Hämta 50 senaste 1-min candles för BTC
print("Hämtar BTC_USDT data från MEXC...")
klines = client.get_klines('BTC_USDT', interval='Min1', limit=50)

if not klines:
 print("FEL: Ingen data från MEXC")
 sys.exit(1)

print(f"Hämtade {len(klines)} candles")

# Extrahera close-priser
closes = [k['close'] for k in klines]

# Beräkna vår RSI
our_rsi = calculate_rsi(closes, period=14)

# Visa kontext
print(f"")
print(f"Senaste close-priser (sista 5): {closes[-5:]}")
print(f"")
print(f"Vår RSI (14-period, 1-min): {our_rsi}")
print(f"")
print(f"Jämför detta värde manuellt mot:")
print(f" TradingView BTC_USDT 1-min RSI(14)")
print(f" MEXC charts BTC_USDT 1-min RSI(14)")
print(f"")
print(f"Acceptabel avvikelse: ±2 poäng")
print(f"(skillnad kan uppstå pga olika startpunkter i beräkningen)")
