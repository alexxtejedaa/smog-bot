import asyncio
import sys
sys.path.insert(0, '.')

from src.clients.mexc import MexcClient
from src.filters.aggregator import FilterAggregator
from src.models import TradingViewAlert
from datetime import datetime, timezone


async def main():
 client = MexcClient(api_key='', api_secret='')
 aggregator = FilterAggregator(client)

 # Test 1: Long-signal för ETH
 print("Test 1: Long-signal ETH")
 alert = TradingViewAlert(
 auth_token="dummy",
 mode="trade",
 signal_type="OG",
 direction="long",
 symbol="ETHUSDT.P",
 timeframe="1",
 price=2500.0,
 timestamp=datetime.now(timezone.utc),
 alert_id="test_eth_long"
 )
 result = await aggregator.evaluate(alert)
 print(f" Passed: {result['passed']}")
 print(f" Skip reason: {result['skip_reason']}")
 print(f" Token RSI 1m: {result['token_rsi_1m']}")
 print(f" Token RSI 5m: {result['token_rsi_5m']}")
 print(f" Token RSI 15m: {result['token_rsi_15m']}")
 print(f" BTC change 15m: {result['btc_context']['change_15m']}%")
 print(f" BTC RSI 1m: {result['btc_context']['rsi_1m']}")
 print()

 # Test 2: Short-signal för SOL
 print("Test 2: Short-signal SOL")
 alert2 = TradingViewAlert(
 auth_token="dummy",
 mode="trade",
 signal_type="OG",
 direction="short",
 symbol="SOLUSDT.P",
 timeframe="1",
 price=150.0,
 timestamp=datetime.now(timezone.utc),
 alert_id="test_sol_short"
 )
 result2 = await aggregator.evaluate(alert2)
 print(f" Passed: {result2['passed']}")
 print(f" Skip reason: {result2['skip_reason']}")
 print(f" Token RSI 1m: {result2['token_rsi_1m']}")
 print()

 # Test 3: TAO long (mer volatil)
 print("Test 3: Long-signal TAO")
 alert3 = TradingViewAlert(
 auth_token="dummy",
 mode="trade",
 signal_type="OG",
 direction="long",
 symbol="TAOUSDT.P",
 timeframe="1",
 price=400.0,
 timestamp=datetime.now(timezone.utc),
 alert_id="test_tao_long"
 )
 result3 = await aggregator.evaluate(alert3)
 print(f" Passed: {result3['passed']}")
 print(f" Skip reason: {result3['skip_reason']}")
 print(f" Token RSI 1m: {result3['token_rsi_1m']}")
 print()

 # Sanity checks
 print("Sanity checks:")
 for r in [result, result2, result3]:
  assert 'passed' in r
  assert 'symbol' in r
  assert 'signal_type' in r
  assert 'direction' in r
  assert 'btc_context' in r
  assert 'evaluated_at' in r
 print(" Alla struktur-checks passerade")
 print()

 # Performance check
 print("Performance: Hur snabb är evaluate()?")
 import time
 start = time.time()
 await aggregator.evaluate(alert)
 elapsed = time.time() - start
 print(f" Andra körningen (BTC cached): {elapsed*1000:.0f}ms")
 print(f" Förväntat: <500ms")


if __name__ == "__main__":
 asyncio.run(main())
