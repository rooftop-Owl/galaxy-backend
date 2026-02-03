# Caduceus Architecture

> Named after Hermes' staff with two intertwined serpents — one wing for channels, one for executors.

## Design Pattern

Inspired by [nanobot](https://github.com/HKUDS/nanobot)'s `BaseChannel` + `MessageBus` pattern, adapted for Galaxy Protocol's filesystem-based order system.

```
┌─────────────┐     ┌────────────┐     ┌─────────────────┐
│  Telegram    │────▶│            │────▶│  HermesExecutor  │
│  Channel     │     │  Message   │     │  (filesystem     │
└─────────────┘     │  Bus       │     │   bridge)        │
                    │            │     └────────┬────────┘
┌─────────────┐     │  inbound   │              │
│  Web         │────▶│  outbound  │◀─────────────┘
│  Channel     │◀────│            │
└─────────────┘     └────────────┘
```

## Components

### MessageBus (`bus.py`)

Async in-memory message router using `asyncio.Queue`.

- **InboundMessage**: Channel → Executor (user request)
- **OutboundMessage**: Executor → Channel (agent response)
- **session_key**: `"{channel}:{chat_id}"` for continuity tracking

No external brokers. No persistence. Queues are ephemeral.

### BaseChannel (`channels/base.py`)

Abstract interface all channels must implement:

| Method | Purpose |
|--------|---------|
| `start()` | Connect to platform, begin receiving |
| `stop()` | Graceful disconnect, cleanup |
| `send(msg)` | Deliver OutboundMessage to user |
| `_handle_message(...)` | Generic handler → publishes to bus |

### TelegramChannel (`channels/telegram.py`)

Full extraction from `bot.py`. Preserves:
- All slash commands (`/status`, `/concerns`, `/order`, `/machines`, `/help`)
- Authorization via `authorized_users` list
- Order creation via filesystem protocol
- Background polling (acknowledgments + outbox)
- Response formatting (compact emoji HTML)
- Multi-machine support (local + SSH)

### WebChannel (`channels/web.py`)

aiohttp WebSocket server with minimal chat UI:
- WebSocket endpoint at `/ws`
- Static HTML/JS served at `/`
- Auto-reconnecting client
- Authorization via chat_id whitelist

### Executor (`executors/base.py`)

Abstract interface for execution backends:

| Method | Purpose |
|--------|---------|
| `execute(order)` | Process order dict, return result dict |

### HermesExecutor (`executors/hermes.py`)

Wraps existing `hermes.py` daemon via filesystem bridge:

1. Write order JSON to `.sisyphus/notepads/galaxy-orders/`
2. Poll for response file (`.sisyphus/notepads/galaxy-order-response-*.md`)
3. Read response and return result dict

**Zero changes to hermes.py required.**

### Gateway (`gateway.py`)

Unified entry point that wires everything together:

1. Load config from `.galaxy/config.json`
2. Instantiate MessageBus
3. Create channels based on config (Telegram if token, Web if enabled)
4. Create HermesExecutor
5. Run `executor_loop` (consume inbound → execute → publish outbound)
6. Run `outbound_dispatcher` (consume outbound → route to channel)
7. Graceful shutdown on SIGINT/SIGTERM

## Message Flow

```
User sends "check tests"
    │
    ▼
TelegramChannel._on_text()
    │
    ├── create_order() → writes .json to galaxy-orders/
    ├── _handle_message() → publishes InboundMessage to bus
    │
    ▼
MessageBus.inbound queue
    │
    ▼
executor_loop() → bus.consume_inbound()
    │
    ▼
HermesExecutor.execute()
    │
    ├── writes order to galaxy-orders/
    ├── waits for response file
    ├── reads response
    │
    ▼
MessageBus.outbound queue
    │
    ▼
outbound_dispatcher() → bus.consume_outbound()
    │
    ▼
TelegramChannel.send() → Telegram API
    │
    ▼
User receives response
```

## Configuration

Configuration lives in `.galaxy/config.json`. Caduceus reads the same config as `bot.py` with optional additions:

```json
{
  "telegram_token": "BOT_TOKEN",
  "authorized_users": [123456789],
  "machines": {
    "local": {
      "host": "localhost",
      "repo_path": "/path/to/project"
    }
  },
  "default_machine": "local",
  "poll_interval": 30,
  "web": {
    "enabled": true,
    "port": 8080,
    "authorized_users": []
  }
}
```

## Design Decisions

1. **No external message broker** — asyncio.Queue is sufficient for single-process gateway
2. **Filesystem bridge** — Preserves existing hermes.py without modifications
3. **Backward compatible** — Same config.json format, new `web` section optional
4. **bot.py preserved** — Can run old system alongside Caduceus during migration
