from abc import ABC, abstractmethod

class ExchangeConnector(ABC):
    """
    Abstract base class defining the interface for all exchange connectors.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the exchange's WebSocket server."""
        raise NotImplementedError

    @abstractmethod
    async def subscribe_symbol(self, symbol: str) -> bool:
        """Subscribe to price updates for a specific symbol."""
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully disconnect from the WebSocket server."""
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        """Check the current connection status."""
        raise NotImplementedError
