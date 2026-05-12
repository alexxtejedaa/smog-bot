import sys
sys.path.insert(0, '.')
from src.filters.rsi import calculate_rsi

# Test 1: Standard test-data från Wikipedia/Investopedia RSI-exempel
# Wilder's original example: 14-period RSI
test_closes = [
 44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00,
 46.03, 46.41, 46.22, 45.64, 46.21
]
rsi = calculate_rsi(test_closes, period=14)
print(f"Test 1 (Wilder example): RSI = {rsi}")
print(f" Forväntat ungefär: 70.46 (klassiskt RSI-värde för detta dataset)")

# Test 2: Stigande trend (ska ge hög RSI)
rising = [100 + i for i in range(20)]
rsi = calculate_rsi(rising, period=14)
print(f"Test 2 (stigande trend): RSI = {rsi}")
print(f" Forväntat: nära 100")

# Test 3: Fallande trend (ska ge låg RSI)
falling = [100 - i for i in range(20)]
rsi = calculate_rsi(falling, period=14)
print(f"Test 3 (fallande trend): RSI = {rsi}")
print(f" Forväntat: nära 0")

# Test 4: För få datapunkter (ska returnera None)
short = [100, 101, 102]
rsi = calculate_rsi(short, period=14)
print(f"Test 4 (för få data): RSI = {rsi}")
print(f" Forväntat: None")

# Test 5: Flat data (allt samma värde)
flat = [100] * 20
rsi = calculate_rsi(flat, period=14)
print(f"Test 5 (flat data): RSI = {rsi}")
print(f" Forväntat: 50.0 (edge case)")
