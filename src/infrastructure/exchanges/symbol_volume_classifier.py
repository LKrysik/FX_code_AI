"""
Symbol Volume Classifier (BUG-008-6)
=====================================

Classifies trading symbols by expected data volume/activity level
to enable dynamic activity timeout thresholds.

High volume symbols (BTC, ETH) expect frequent updates (60s threshold)
Medium volume symbols expect regular updates (120s threshold)
Low volume/unknown symbols may have sparse updates (300s threshold)

This prevents false positive connection closures for low-volume symbols
while maintaining fast detection for high-volume trading pairs.
"""

from enum import Enum
from typing import Dict, Optional, Set


class SymbolVolumeCategory(Enum):
    """
    Symbol volume classification for activity timeout thresholds.

    HIGH: Top trading pairs (BTC, ETH, SOL, XRP, BNB) - expect frequent updates
    MEDIUM: Common altcoins - expect regular updates
    LOW: Unknown/obscure symbols - may have sparse updates
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActivityType(Enum):
    """
    Types of activity that can occur on a WebSocket connection.

    Each type has a weight indicating its importance and whether
    it should reset the data activity timer.

    Trade/Orderbook: HIGH weight, resets timer (real market activity)
    System: MEDIUM weight, resets timer (exchange health)
    Ping/Pong: LOW weight, does NOT reset timer (just connection check)
    """
    TRADE = ("trade", True, "high")
    ORDERBOOK = ("orderbook", True, "high")
    DEPTH_SNAPSHOT = ("depth_snapshot", True, "high")
    SYSTEM = ("system", True, "medium")
    PING_PONG = ("ping_pong", False, "low")

    def __init__(self, type_name: str, resets_timer: bool, weight: str):
        self.type_name = type_name
        self.resets_timer = resets_timer
        self.weight = weight


# Default activity thresholds per volume category (in seconds)
ACTIVITY_THRESHOLDS: Dict[SymbolVolumeCategory, int] = {
    SymbolVolumeCategory.HIGH: 60,    # 1 minute for high volume
    SymbolVolumeCategory.MEDIUM: 120,  # 2 minutes for medium volume
    SymbolVolumeCategory.LOW: 300,     # 5 minutes for low volume
}

# High volume symbols - top trading pairs with frequent activity
# These are major crypto pairs that typically have trades every few seconds
HIGH_VOLUME_SYMBOLS: Set[str] = {
    # Bitcoin pairs
    "BTCUSDT", "BTC_USDT", "BTCUSD", "BTC_USD",
    # Ethereum pairs
    "ETHUSDT", "ETH_USDT", "ETHUSD", "ETH_USD",
    # Other top-10 by volume
    "SOLUSDT", "SOL_USDT",
    "XRPUSDT", "XRP_USDT",
    "BNBUSDT", "BNB_USDT",
    "DOGEUSDT", "DOGE_USDT",
    "ADAUSDT", "ADA_USDT",
    "AVAXUSDT", "AVAX_USDT",
    "TRXUSDT", "TRX_USDT",
    "TONUSDT", "TON_USDT",
}

# Medium volume symbols - common altcoins in top 100
# Typically have trades every 10-30 seconds
MEDIUM_VOLUME_SYMBOLS: Set[str] = {
    # Top 20-50 altcoins
    "DOTUSDT", "DOT_USDT",
    "LINKUSDT", "LINK_USDT",
    "MATICUSDT", "MATIC_USDT",
    "SHIBUSDT", "SHIB_USDT",
    "LTCUSDT", "LTC_USDT",
    "ATOMUSDT", "ATOM_USDT",
    "NEARUSDT", "NEAR_USDT",
    "APTUSDT", "APT_USDT",
    "OPUSDT", "OP_USDT",
    "ARBUSDT", "ARB_USDT",
    "FILUSDT", "FIL_USDT",
    "INJUSDT", "INJ_USDT",
    "IMXUSDT", "IMX_USDT",
    "SUIUSDT", "SUI_USDT",
    "SEIUSDT", "SEI_USDT",
    "TIAUSDT", "TIA_USDT",
    "JUPUSDT", "JUP_USDT",
    "WLDUSDT", "WLD_USDT",
    "STXUSDT", "STX_USDT",
    "PEPEUSDT", "PEPE_USDT",
    "WIFUSDT", "WIF_USDT",
    "BONKUSDT", "BONK_USDT",
    "FLOKIUSDT", "FLOKI_USDT",
}


class SymbolVolumeClassifier:
    """
    Classifies symbols by expected data volume for activity timeout thresholds.

    This enables dynamic timeout thresholds that adapt to the expected
    activity level of each trading pair, reducing false positive
    connection closures for low-volume symbols.

    Usage:
        classifier = SymbolVolumeClassifier()
        category = classifier.get_category("BTCUSDT")  # SymbolVolumeCategory.HIGH
        threshold = classifier.get_threshold("BTCUSDT")  # 60 (seconds)
    """

    def __init__(
        self,
        thresholds: Optional[Dict[SymbolVolumeCategory, int]] = None,
        high_volume_symbols: Optional[Set[str]] = None,
        medium_volume_symbols: Optional[Set[str]] = None,
    ):
        """
        Initialize the classifier with optional custom configurations.

        Args:
            thresholds: Custom threshold values per category (overrides defaults)
            high_volume_symbols: Custom set of high volume symbols
            medium_volume_symbols: Custom set of medium volume symbols
        """
        self.thresholds = thresholds or ACTIVITY_THRESHOLDS.copy()
        self.high_volume_symbols = high_volume_symbols or HIGH_VOLUME_SYMBOLS.copy()
        self.medium_volume_symbols = medium_volume_symbols or MEDIUM_VOLUME_SYMBOLS.copy()

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for consistent lookup.

        Handles variations like BTCUSDT, BTC_USDT, btcusdt, etc.
        """
        return symbol.upper().replace("_", "")

    def get_category(self, symbol: str) -> SymbolVolumeCategory:
        """
        Get the volume category for a trading symbol.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT", "BTC_USDT")

        Returns:
            SymbolVolumeCategory indicating expected activity level
        """
        normalized = self.normalize_symbol(symbol)

        # Check high volume first
        for high_symbol in self.high_volume_symbols:
            if self.normalize_symbol(high_symbol) == normalized:
                return SymbolVolumeCategory.HIGH

        # Check medium volume
        for medium_symbol in self.medium_volume_symbols:
            if self.normalize_symbol(medium_symbol) == normalized:
                return SymbolVolumeCategory.MEDIUM

        # Default to LOW for unknown symbols
        return SymbolVolumeCategory.LOW

    def get_threshold(self, symbol: str) -> int:
        """
        Get the activity timeout threshold for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Timeout threshold in seconds
        """
        category = self.get_category(symbol)
        return self.thresholds[category]

    def get_all_thresholds(self) -> Dict[SymbolVolumeCategory, int]:
        """Get all configured thresholds."""
        return self.thresholds.copy()


def parse_symbol_list(symbols_string: str) -> Set[str]:
    """
    Parse comma-separated symbol list from config string.

    Args:
        symbols_string: Comma-separated symbols like "BTCUSDT,ETHUSDT,SOLUSDT"

    Returns:
        Set of normalized symbols
    """
    if not symbols_string or not symbols_string.strip():
        return set()

    symbols = set()
    for symbol in symbols_string.split(","):
        symbol = symbol.strip().upper()
        if symbol:
            symbols.add(symbol)
            # Also add underscore variant for MEXC format compatibility
            if "_" not in symbol and "USDT" in symbol:
                symbols.add(symbol.replace("USDT", "_USDT"))
    return symbols


def create_classifier_from_settings(
    high_threshold: int = 60,
    medium_threshold: int = 120,
    low_threshold: int = 300,
    high_volume_symbols: Optional[str] = None,
    medium_volume_symbols: Optional[str] = None,
) -> SymbolVolumeClassifier:
    """
    Factory function to create classifier from settings values.

    Args:
        high_threshold: Timeout for high volume symbols (default: 60s)
        medium_threshold: Timeout for medium volume symbols (default: 120s)
        low_threshold: Timeout for low volume symbols (default: 300s)
        high_volume_symbols: Comma-separated high volume symbols (or None for defaults)
        medium_volume_symbols: Comma-separated medium volume symbols (or None for defaults)

    Returns:
        Configured SymbolVolumeClassifier
    """
    thresholds = {
        SymbolVolumeCategory.HIGH: high_threshold,
        SymbolVolumeCategory.MEDIUM: medium_threshold,
        SymbolVolumeCategory.LOW: low_threshold,
    }

    # Parse symbol lists from config or use defaults
    high_symbols = parse_symbol_list(high_volume_symbols) if high_volume_symbols else None
    medium_symbols = parse_symbol_list(medium_volume_symbols) if medium_volume_symbols else None

    return SymbolVolumeClassifier(
        thresholds=thresholds,
        high_volume_symbols=high_symbols,
        medium_volume_symbols=medium_symbols,
    )
