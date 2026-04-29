"""
New Logging Module for Paper Trading
Implements PnL calculation, slippage simulation, and CSV logging
per DESIGN_NEW_LOGGING.md
"""

import csv
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

# DCA Configuration
QTY_L1_MULTIPLIER = 3
QTY_L2_MULTIPLIER = 5

# Fee Configuration (MEXC Futures)
# Paper-mode assumptions: Entry/L1/L2 are LIMIT (maker), SL is MARKET (taker), TP is LIMIT (maker)
MAKER_FEE_RATE = 0.0001  # 0.01% for LIMIT orders
TAKER_FEE_RATE = 0.0005  # 0.05% for MARKET orders

# Slippage Configuration (SL only)
SLIPPAGE_MIN = 0.0005  # 0.05%
SLIPPAGE_MAX = 0.0010  # 0.10%


class FillDetail:
    """Represents a single fill (Entry, L1, L2)"""
    
    def __init__(self, price: float, qty_tokens: float, order_type: str = "LIMIT"):
        self.price = price
        self.qty_tokens = qty_tokens
        self.order_type = order_type  # "LIMIT" or "MARKET"
        self.notional = price * qty_tokens


class PnLCalculator:
    """Calculates PnL per DESIGN_NEW_LOGGING.md formulas"""

    @staticmethod
    def calculate_avg_entry_price(
        entry_price: float,
        entry_qty_tokens: float,
        l1_price: Optional[float] = None,
        l1_qty_tokens: Optional[float] = None,
        l2_price: Optional[float] = None,
        l2_qty_tokens: Optional[float] = None,
    ) -> float:
        """
        Calculate weighted average entry price for 1-3 fills.
        
        Formula:
        avg_entry_price = (entry_price × entry_qty + l1_price × l1_qty + l2_price × l2_qty) / total_qty
        """
        numerator = entry_price * entry_qty_tokens
        denominator = entry_qty_tokens

        if l1_qty_tokens is not None and l1_qty_tokens > 0:
            numerator += l1_price * l1_qty_tokens
            denominator += l1_qty_tokens

        if l2_qty_tokens is not None and l2_qty_tokens > 0:
            numerator += l2_price * l2_qty_tokens
            denominator += l2_qty_tokens

        return numerator / denominator if denominator > 0 else entry_price

    @staticmethod
    def calculate_total_qty_tokens(
        entry_qty_tokens: float,
        l1_qty_tokens: Optional[float] = None,
        l2_qty_tokens: Optional[float] = None,
    ) -> float:
        """Sum of all filled quantities in tokens"""
        total = entry_qty_tokens
        if l1_qty_tokens is not None and l1_qty_tokens > 0:
            total += l1_qty_tokens
        if l2_qty_tokens is not None and l2_qty_tokens > 0:
            total += l2_qty_tokens
        return total

    @staticmethod
    def calculate_notional_value(avg_entry_price: float, total_qty_tokens: float) -> float:
        """
        Notional = avg_entry_price × total_qty_tokens
        NOTE: Does NOT multiply by contract_size
        contract_size is for logging/verification only
        """
        return avg_entry_price * total_qty_tokens

    @staticmethod
    def calculate_margin_used(notional_value: float, leverage: int) -> float:
        """margin = notional / leverage"""
        return notional_value / leverage

    @staticmethod
    def calculate_gross_pnl(
        direction: str,  # "LONG" or "SHORT"
        entry_notional: float,
        close_notional: float,
    ) -> float:
        """
        Calculate gross PnL before fees using notional values.
        
        This formula is mathematically correct for both single and split closes.
        
        For LONG:  gross_pnl = close_notional - entry_notional
        For SHORT: gross_pnl = entry_notional - close_notional
        """
        if direction == "LONG":
            return close_notional - entry_notional
        elif direction == "SHORT":
            return entry_notional - close_notional
        else:
            raise ValueError(f"Invalid direction: {direction}")

    @staticmethod
    def calculate_entry_fees(
        entry_qty_tokens: float,
        entry_price: float,
        l1_qty_tokens: Optional[float] = None,
        l1_price: Optional[float] = None,
        l2_qty_tokens: Optional[float] = None,
        l2_price: Optional[float] = None,
    ) -> float:
        """
        Calculate total entry fees for all fills (Entry + L1 + L2).
        
        All entry fills are LIMIT orders → maker_fee = 0.0001 (0.01%)
        
        Formula:
        entry_fees = (entry_notional × maker_fee)
                   + (l1_notional × maker_fee) [if L1 filled]
                   + (l2_notional × maker_fee) [if L2 filled]
        """
        entry_notional = entry_price * entry_qty_tokens
        entry_fees = entry_notional * MAKER_FEE_RATE
        
        if l1_qty_tokens is not None and l1_qty_tokens > 0:
            l1_notional = l1_price * l1_qty_tokens
            entry_fees += l1_notional * MAKER_FEE_RATE
        
        if l2_qty_tokens is not None and l2_qty_tokens > 0:
            l2_notional = l2_price * l2_qty_tokens
            entry_fees += l2_notional * MAKER_FEE_RATE
        
        return entry_fees

    @staticmethod
    def calculate_exit_fee(
        close_notional: float,
        close_reason: str,  # "TP_HIT", "SL_HIT", "MANUAL"
    ) -> float:
        """
        Calculate exit fee based on close reason.
        
        Paper-mode assumptions:
        - TP_HIT: LIMIT order → maker_fee = 0.0001 (0.01%)
        - SL_HIT: MARKET order (worst-case) → taker_fee = 0.0005 (0.05%)
        - MANUAL: LIMIT order → maker_fee = 0.0001 (0.01%)
        """
        if close_reason == "SL_HIT":
            return close_notional * TAKER_FEE_RATE  # 0.05%
        else:  # TP_HIT or MANUAL
            return close_notional * MAKER_FEE_RATE  # 0.01%

    @staticmethod
    def calculate_fees_total(
        entry_qty_tokens: float,
        entry_price: float,
        l1_qty_tokens: Optional[float],
        l1_price: Optional[float],
        l2_qty_tokens: Optional[float],
        l2_price: Optional[float],
        close_notional: float,
        close_reason: str,
    ) -> float:
        """
        Total fees = entry_fees + exit_fee
        """
        entry_fees = PnLCalculator.calculate_entry_fees(
            entry_qty_tokens, entry_price, l1_qty_tokens, l1_price, l2_qty_tokens, l2_price
        )
        exit_fee = PnLCalculator.calculate_exit_fee(close_notional, close_reason)
        return entry_fees + exit_fee

    @staticmethod
    def calculate_net_pnl(gross_pnl: float, fees_total: float) -> float:
        """net_pnl = gross_pnl - fees"""
        return gross_pnl - fees_total

    @staticmethod
    def calculate_close_price(
        setup_price: float,
        close_reason: str,  # "TP_HIT", "SL_HIT", "MANUAL"
        direction: str,  # "LONG" or "SHORT"
        slippage_pct: Optional[float] = None,
    ) -> Tuple[float, float]:
        """
        Determine close_price and slippage_applied based on close reason.
        
        TP_HIT: No slippage, close_price = setup_tp_price
        SL_HIT: Apply slippage in adverse direction
          - LONG SL: close_price = setup_sl × (1 - slippage_pct)  [price goes lower]
          - SHORT SL: close_price = setup_sl × (1 + slippage_pct)  [price goes higher]
        MANUAL: No slippage, close_price = market price (handled externally)
        
        Returns: (close_price, slippage_pct_used)
        """
        if close_reason == "TP_HIT":
            return setup_price, 0.0
        elif close_reason == "SL_HIT":
            if slippage_pct is None:
                # Generate random slippage between SLIPPAGE_MIN and SLIPPAGE_MAX
                slippage_pct = random.uniform(SLIPPAGE_MIN, SLIPPAGE_MAX)

            if direction == "LONG":
                # LONG SL: price goes lower (adverse slippage subtracts from SL)
                close_price = setup_price * (1 - slippage_pct)
            elif direction == "SHORT":
                # SHORT SL: price goes higher (adverse slippage adds to SL)
                close_price = setup_price * (1 + slippage_pct)
            else:
                raise ValueError(f"Invalid direction: {direction}")

            return close_price, slippage_pct
        elif close_reason == "MANUAL":
            return setup_price, 0.0
        else:
            raise ValueError(f"Invalid close_reason: {close_reason}")

    @staticmethod
    def calculate_slippage_applied(
        close_price: float, setup_sl_price: float, total_qty_tokens: float
    ) -> float:
        """
        slippage_applied = |close_price - setup_sl_price| × total_qty_tokens
        USDT impact of slippage on entire position
        """
        return abs(close_price - setup_sl_price) * total_qty_tokens


class TradeLogger:
    """Logs trades to CSV with all calculated fields"""

    CSV_COLUMNS = [
        "timestamp",
        "symbol",
        "direction",
        "contract_size",
        "leverage",
        "entry_price",
        "l1_price",
        "l2_price",
        "entry_qty_tokens",
        "l1_qty_tokens",
        "l2_qty_tokens",
        "total_qty_tokens",
        "avg_entry_price",
        "close_price",
        "close_reason",
        "slippage_pct",
        "slippage_applied",
        "notional_value",
        "margin_used",
        "gross_pnl",
        "fees_total",
        "net_pnl",
        "balance_before",
        "balance_after",
        "hour_utc",
        "day_of_week",
        "swing_age",
        "range_pct",
        "ny_open_flag",
        "price_vs_entry_pct",
        "atr_14",
        "rsi_14",
        "volume_ratio",
        "ema_50_dist_pct",
        "slope_15m",
        "spread_pct",
        "slope_1h",
        "trend_alignment",
        "btc_move_1h",
    ]

    def __init__(self, log_file_path: str = "logs/trade_log_v2.csv"):
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create CSV file with headers if it doesn't exist
        if not self.log_file_path.exists():
            with open(self.log_file_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
                writer.writeheader()

    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """
        Log a completed trade to CSV.
        
        Args:
            trade_data: Dictionary with all required fields
        """
        # Ensure all columns are present
        row = {col: trade_data.get(col, "") for col in self.CSV_COLUMNS}

        with open(self.log_file_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writerow(row)

        logger.info(f"Trade logged: {trade_data['symbol']} {trade_data['direction']} net_pnl={trade_data['net_pnl']:.2f}")


def calculate_trade_pnl(
    symbol: str,
    direction: str,
    contract_size: float,
    leverage: int,
    entry_price: float,
    l1_price: Optional[float],
    l2_price: Optional[float],
    entry_qty_tokens: float,
    l1_qty_tokens: Optional[float],
    l2_qty_tokens: Optional[float],
    close_reason: str,
    setup_tp_price: Optional[float] = None,
    setup_sl_price: Optional[float] = None,
    market_price_at_close: Optional[float] = None,
    close_segments: Optional[List[Tuple[float, float]]] = None,
    balance_before: float = 5000.0,
) -> Dict[str, Any]:
    """
    Complete PnL calculation for a trade.
    
    Args:
        close_segments: Optional list of (close_price, close_qty) tuples for split closes.
                       If provided, close_notional = sum(price × qty for each segment).
                       If not provided, uses market_price_at_close × total_qty (single close).
    
    Returns dictionary with all calculated fields ready for logging.
    
    Steps:
    1. Calculate entry_notional (sum of all entry fills)
    2. Calculate close_notional (sum of all close segments or single close)
    3. Calculate total quantity in tokens
    4. Calculate margin used
    5. Determine close price and slippage (for logging; not used in PnL calc)
    6. Calculate gross PnL from notional difference
    7. Calculate entry fees (all fills are LIMIT → maker)
    8. Calculate exit fee (depends on close_reason)
    9. Calculate net PnL
    10. Calculate balance after trade
    """
    calculator = PnLCalculator()

    # Step 1: Calculate entry_notional (sum of all entry fills)
    entry_notional = (entry_price * entry_qty_tokens)
    if l1_qty_tokens is not None and l1_qty_tokens > 0:
        entry_notional += l1_price * l1_qty_tokens
    if l2_qty_tokens is not None and l2_qty_tokens > 0:
        entry_notional += l2_price * l2_qty_tokens

    # Step 2: Calculate total quantity in tokens (for calculations)
    total_qty_tokens = calculator.calculate_total_qty_tokens(
        entry_qty_tokens, l1_qty_tokens, l2_qty_tokens
    )

    # Step 3: Determine close_price and close_notional
    if close_segments is not None and len(close_segments) > 0:
        # Split close: sum of (price × qty) for each segment
        close_notional = sum(price * qty for price, qty in close_segments)
        # For close_price logging: weighted average
        total_close_qty = sum(qty for _, qty in close_segments)
        close_price = close_notional / total_close_qty if total_close_qty > 0 else entry_price
        slippage_pct = 0.0
        slippage_applied = 0.0
    elif close_reason == "TP_HIT":
        # TP hit: use setup_tp_price, no slippage
        close_price, slippage_pct = calculator.calculate_close_price(
            setup_tp_price, close_reason, direction
        )
        close_notional = close_price * total_qty_tokens
        slippage_applied = 0.0
    elif close_reason == "SL_HIT":
        # SL hit: use setup_sl_price with random slippage
        close_price, slippage_pct = calculator.calculate_close_price(
            setup_sl_price, close_reason, direction
        )
        close_notional = close_price * total_qty_tokens
        slippage_applied = calculator.calculate_slippage_applied(
            close_price, setup_sl_price, total_qty_tokens
        )
    elif close_reason == "MANUAL":
        # Manual close: use provided market_price_at_close (from MEXC validation)
        close_price = market_price_at_close or entry_price
        close_notional = close_price * total_qty_tokens
        slippage_pct = 0.0
        slippage_applied = 0.0
    else:
        raise ValueError(f"Invalid close_reason: {close_reason}")

    # Step 4: Calculate average prices for logging (not used in PnL calc)
    avg_entry_price = entry_notional / total_qty_tokens if total_qty_tokens > 0 else entry_price
    notional_value = entry_notional  # Use entry_notional for consistency

    # Step 5: Calculate margin used
    margin_used = calculator.calculate_margin_used(notional_value, leverage)

    # Step 6: Calculate gross PnL from notional difference
    gross_pnl = calculator.calculate_gross_pnl(
        direction, entry_notional, close_notional
    )

    # Step 7-8: Calculate total fees (entry + exit, with proper fee rates)
    fees_total = calculator.calculate_fees_total(
        entry_qty_tokens, entry_price,
        l1_qty_tokens, l1_price,
        l2_qty_tokens, l2_price,
        close_notional, close_reason
    )

    # Step 9: Calculate net PnL
    net_pnl = calculator.calculate_net_pnl(gross_pnl, fees_total)

    # Step 10: Calculate balance after trade
    balance_after = balance_before + net_pnl

    # Return complete trade data
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "direction": direction,
        "contract_size": contract_size,
        "leverage": leverage,
        "entry_price": round(entry_price, 8),
        "l1_price": round(l1_price, 8) if l1_price is not None else "",
        "l2_price": round(l2_price, 8) if l2_price is not None else "",
        "entry_qty_tokens": round(entry_qty_tokens, 10),
        "l1_qty_tokens": round(l1_qty_tokens, 10) if l1_qty_tokens is not None else "",
        "l2_qty_tokens": round(l2_qty_tokens, 10) if l2_qty_tokens is not None else "",
        "total_qty_tokens": round(total_qty_tokens, 10),
        "avg_entry_price": round(avg_entry_price, 8),
        "close_price": round(close_price, 8),
        "close_reason": close_reason,
        "slippage_pct": round(slippage_pct, 6),
        "slippage_applied": round(slippage_applied, 6),
        "notional_value": round(notional_value, 2),
        "margin_used": round(margin_used, 2),
        "gross_pnl": round(gross_pnl, 2),
        "fees_total": round(fees_total, 6),
        "net_pnl": round(net_pnl, 2),
        "balance_before": round(balance_before, 2),
        "balance_after": round(balance_after, 2),
        "hour_utc": datetime.utcnow().hour,
        "day_of_week": datetime.utcnow().weekday(),
        "swing_age": "",  # Filled by bot
        "range_pct": "",  # Filled by bot
        "ny_open_flag": "",  # Filled by bot
        "price_vs_entry_pct": "",  # Filled by bot
        "atr_14": "",  # Filled by bot
        "rsi_14": "",  # Filled by bot
        "volume_ratio": "",  # Filled by bot
        "ema_50_dist_pct": "",  # Filled by bot
        "slope_15m": "",  # Filled by bot
        "spread_pct": "",  # Filled by bot
        "slope_1h": "",  # Filled by bot
        "trend_alignment": "",  # Filled by bot
        "btc_move_1h": "",  # Filled by bot
    }
