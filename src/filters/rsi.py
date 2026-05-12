"""
RSI (Relative Strength Index) beräkningar.

Beräknar RSI från stängningspriser med Wilder's smoothing-formel.
"""


def calculate_rsi(closes: list[float], period: int = 14) -> float | None:
    """
    Beräknar Relative Strength Index (RSI) från stängningspriser.
    
    Args:
        closes: Lista med stängningspriser, senaste sist
        period: RSI-period (standard 14)
    
    Returns:
        RSI-värde mellan 0-100, eller None om för få datapunkter
    
    Använder Wilder's smoothing-formel:
    - Första genomsnittet: enkelt medelvärde
    - Senare genomsnitt: (prev_avg * (period - 1) + new_value) / period
    """
    
    # Kräver minst period + 1 datapunkter för att beräkna RSI
    if len(closes) < period + 1:
        return None
    
    # Beräkna prisförändringar
    changes = []
    for i in range(1, len(closes)):
        changes.append(closes[i] - closes[i - 1])
    
    # Separera upp- och nedgångar
    gains = [change if change > 0 else 0 for change in changes]
    losses = [abs(change) if change < 0 else 0 for change in changes]
    
    # Wilder's smoothing: första genomsnittet är enkelt medelvärde
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Wilder's smoothing för återstående värden
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    # Undvik division med noll
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    
    # Beräkna RS och RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)
