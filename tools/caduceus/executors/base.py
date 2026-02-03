"""Base executor interface for Caduceus gateway.

All executor implementations must inherit from Executor ABC.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class Executor(ABC):
    """Abstract base class for all executor implementations.

    Executors handle the actual execution of user requests - running code,
    querying systems, generating responses, etc.

    Architecture:
        MessageBus → Executor.execute(order) → MessageBus
    """

    @abstractmethod
    async def execute(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an order and return the result.

        Args:
            order: Order dictionary containing:
                - payload (str): The actual command/request to execute
                - timestamp (float): When the order was created
                - order_id (str): Unique identifier for this order
                - Additional executor-specific fields

        Returns:
            Result dictionary containing:
                - success (bool): Whether execution succeeded
                - response_text (str): The response to send back
                - error (str, optional): Error message if execution failed
                - Additional executor-specific fields

        Raises:
            Exception: If execution fails catastrophically
        """
        pass
