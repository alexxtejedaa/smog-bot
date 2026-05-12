import asyncio
import sys
import time
sys.path.insert(0, '.')

from src.clients.mexc import MexcClient
from src.filters.btc_tracking import BtcTracker


async def main():
 client = MexcClient(api_key='', api_secret='')
 tracker = BtcTracker(client)

 # Test 1: Första anropet - hämtar från MEXC
 print("Test 1: Första anrop (hämtar från MEXC)")
 start = time.time()
 context = await tracker.get_context()
 elapsed = time.time() - start
 print(f" Tid: {elapsed:.2f}s (förväntat <2s med parallella anrop)")
 print(f" RSI 1m: {context['rsi_1m']}")
 print(f" RSI 5m: {context['rsi_5m']}")
 print(f" RSI 15m: {context['rsi_15m']}")
 print(f" Change 1m: {context['change_1m']}%")
 print(f" Change 5m: {context['change_5m']}%")
 print(f" Change 15m: {context['change_15m']}%")
 print(f" Volatility 1m: {context['volatility_1m']}")
 print(f" Timestamp: {context['timestamp']}")
 print()
 print()

 # Test 2: Andra anropet inom 10s - ska komma från cache
 print("Test 2: Andra anrop direkt efter (ska komma från cache)")
 start = time.time()
 context2 = await tracker.get_context()
 elapsed = time.time() - start
 print(f" Tid: {elapsed:.4f}s (förväntat <0.01s från cache)")
 print(f" Samma timestamp som test 1: {context['timestamp'] == context2['timestamp']}")
 print()

 # Test 3: Vänta 11 sek och prova igen - cache ska ha gått ut
 print("Test 3: Väntar 11s sen anropar igen (cache ska ha gått ut)")
 await asyncio.sleep(11)
 start = time.time()
 context3 = await tracker.get_context()
 elapsed = time.time() - start
 print(f" Tid: {elapsed:.2f}s (förväntat >0.5s, ny hämtning)")
 print(f" Ny timestamp: {context3['timestamp'] != context['timestamp']}")
 print()

 # Sanity checks
 print("Sanity checks:")
 if context['rsi_1m'] is not None:
     assert 0 <= context['rsi_1m'] <= 100, f"RSI 1m ogiltigt: {context['rsi_1m']}"
 if context['rsi_5m'] is not None:
     assert 0 <= context['rsi_5m'] <= 100, f"RSI 5m ogiltigt: {context['rsi_5m']}"
 if context['rsi_15m'] is not None:
     assert 0 <= context['rsi_15m'] <= 100, f"RSI 15m ogiltigt: {context['rsi_15m']}"
 assert context['change_1m'] is not None, "Change 1m är None"
 assert context['change_5m'] is not None, "Change 5m är None"
 assert context['change_15m'] is not None, "Change 15m är None"
 if context['volatility_1m'] is not None:
     assert context['volatility_1m'] >= 0, f"Volatility negativ: {context['volatility_1m']}"
 print(" Alla sanity checks passerade")


if __name__ == "__main__":
 asyncio.run(main())
