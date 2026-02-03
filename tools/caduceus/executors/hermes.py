"""HermesExecutor - Wraps existing hermes.py daemon via filesystem bridge."""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any

from caduceus.executors.base import Executor


class HermesExecutor(Executor):
    """Executor that delegates to existing hermes.py daemon.

    Uses the filesystem protocol:
    1. Write order JSON to .sisyphus/notepads/galaxy-orders/
    2. Wait for response file to appear
    3. Read response and return result

    This preserves the existing hermes.py daemon without modifications.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize HermesExecutor.

        Args:
            config: Configuration dict containing:
                - orders_dir (str): Path to orders directory
                - timeout (int): Max wait time for response (default: 180s)
                - poll_interval (float): How often to check for response (default: 1.0s)
        """
        self.orders_dir = Path(
            config.get("orders_dir", ".sisyphus/notepads/galaxy-orders")
        )
        self.notepads_dir = self.orders_dir.parent
        self.timeout = config.get("timeout", 180)  # 3 minutes
        self.poll_interval = config.get("poll_interval", 1.0)

        # Ensure orders directory exists
        self.orders_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order via hermes.py filesystem bridge.

        Args:
            order: Order dict containing:
                - payload (str): The command to execute
                - timestamp (float): When order was created
                - order_id (str): Unique identifier

        Returns:
            Result dict containing:
                - success (bool): Whether execution succeeded
                - response_text (str): The response from hermes
                - error (str, optional): Error message if failed
        """
        order_id = order.get("order_id", f"order-{int(time.time())}")
        payload = order.get("payload", "")

        if not payload:
            return {"success": False, "response_text": "", "error": "Empty payload"}

        try:
            # Write order file
            order_file = self.orders_dir / f"{order_id}.json"
            order_file.write_text(
                json.dumps(
                    {
                        "payload": payload,
                        "timestamp": order.get("timestamp", time.time()),
                        "order_id": order_id,
                        **{
                            k: v
                            for k, v in order.items()
                            if k not in ["payload", "timestamp", "order_id"]
                        },
                    },
                    indent=2,
                )
            )

            # Wait for response file
            response_file = self.notepads_dir / f"galaxy-order-response-{order_id}.md"
            start_time = time.time()

            while time.time() - start_time < self.timeout:
                if response_file.exists():
                    # Read response
                    response_text = response_file.read_text()

                    # Clean up response file
                    try:
                        response_file.unlink()
                    except OSError:
                        pass

                    return {
                        "success": True,
                        "response_text": response_text,
                    }

                await asyncio.sleep(self.poll_interval)

            # Timeout - clean up order file if still exists
            if order_file.exists():
                try:
                    order_file.unlink()
                except OSError:
                    pass

            return {
                "success": False,
                "response_text": "",
                "error": f"Timeout after {self.timeout}s waiting for response",
            }

        except Exception as e:
            return {
                "success": False,
                "response_text": "",
                "error": f"Execution error: {str(e)}",
            }
