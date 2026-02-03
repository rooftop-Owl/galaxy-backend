# Migration Guide: bot.py → Caduceus Gateway

## Overview

Caduceus replaces `bot.py` + `hermes.py` with a unified gateway. Both systems can run simultaneously during transition.

## Prerequisites

- Python 3.10+
- `pip install aiohttp` (new dependency for WebChannel)
- Existing `.galaxy/config.json` works unchanged

## Step-by-Step Migration

### 1. Install New Dependency

```bash
pip install aiohttp
```

### 2. Test Gateway in Test Mode

```bash
python3 galaxy-protocol/tools/caduceus/gateway.py --test-mode --config .galaxy/config.json
```

Expected output:
```
Caduceus gateway — test mode
  Channels: telegram
  Executor: HermesExecutor
  Orders dir: ...
Config valid. Exiting test mode.
```

### 3. Enable Web Channel (Optional)

Add to `.galaxy/config.json`:
```json
{
  "web": {
    "enabled": true,
    "port": 8080,
    "authorized_users": []
  }
}
```

### 4. Run Both Systems in Parallel

```bash
# Keep existing system running
# systemctl status galaxy         # Don't stop yet
# systemctl status hermes         # Keep running

# Start Caduceus alongside
python3 galaxy-protocol/tools/caduceus/gateway.py --config .galaxy/config.json &
```

**Note**: TelegramChannel and bot.py will both respond to messages. Stop one before testing the other.

### 5. Verify Functionality

```bash
# Send a test message via Telegram
# Check order files created
ls .sisyphus/notepads/galaxy-orders/

# If web enabled, check UI
curl -s http://localhost:8080/ | grep -q 'Caduceus' && echo "Web UI OK"
```

### 6. Switch Systemd Services

```bash
# Stop old services
sudo systemctl stop galaxy
sudo systemctl stop hermes

# Install new service
sudo ./galaxy-protocol/tools/caduceus/install-service.sh

# Start Caduceus
sudo systemctl enable --now caduceus-gateway

# Verify
sudo systemctl status caduceus-gateway
journalctl -u caduceus-gateway -f
```

### 7. Verify After Switch

- [ ] Telegram bot responds to messages
- [ ] `/status` command works
- [ ] `/order` command creates order files
- [ ] Orders get processed (hermes.py still runs as daemon)
- [ ] Responses appear in Telegram
- [ ] Web UI loads (if enabled)

## Rollback

If issues are found after switching:

```bash
# Stop Caduceus
sudo systemctl stop caduceus-gateway

# Restart old services
sudo systemctl start galaxy
sudo systemctl start hermes

# Verify old system works
sudo systemctl status galaxy
sudo systemctl status hermes
```

No data is lost — both systems use the same filesystem protocol.

## Configuration Differences

| Feature | bot.py | Caduceus |
|---------|--------|----------|
| Config file | Same `.galaxy/config.json` | Same, + optional `web` section |
| Telegram | Always on | Enabled if `telegram_token` present |
| Web UI | Not available | Enabled if `web.enabled: true` |
| Hermes | Separate process | Wrapped via HermesExecutor |
| Order format | Same JSON | Same JSON (backward compatible) |
| Response format | Same markdown | Same markdown |

## Troubleshooting

**Gateway won't start**: Check `python3 gateway.py --test-mode` for config validation errors.

**No Telegram responses**: Ensure only ONE of bot.py/Caduceus is running (both listen on same token).

**Web UI not loading**: Check `web.enabled: true` in config and port availability.

**Orders not processing**: Hermes daemon must still be running (Caduceus wraps it, doesn't replace it).
