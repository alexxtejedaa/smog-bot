"""
Symbol mapping mellan TradingView-format och MEXC-format

TradingView: ETHUSDT.P
MEXC: ETH_USDT
"""


def tradingview_to_mexc(tv_symbol: str) -> str:
    """
    Converts TradingView symbol to MEXC format.
    
    Examples:
    ETHUSDT.P -> ETH_USDT
    SOLUSDT.P -> SOL_USDT
    LINKUSDT.P -> LINK_USDT
    """
    # Remove .P suffix (perpetual indicator)
    if tv_symbol.endswith(".P"):
        tv_symbol = tv_symbol[:-2]
    
    # Find USDT position and split
    if tv_symbol.endswith("USDT"):
        base = tv_symbol[:-4]
        return f"{base}_USDT"
    
    raise ValueError(f"Unsupported symbol format: {tv_symbol}")


def mexc_to_tradingview(mexc_symbol: str) -> str:
    """Converts MEXC symbol back to TradingView format"""
    if "_USDT" in mexc_symbol:
        base = mexc_symbol.replace("_USDT", "")
        return f"{base}USDT.P"
    
    raise ValueError(f"Unsupported symbol format: {mexc_symbol}")
