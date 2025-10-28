# API Documentation

This directory contains API specifications for the FX Cryptocurrency Trading System.

## Available APIs

- **[REST.md](REST.md)** - REST API specification for CRUD operations
- **[WEBSOCKET.md](WEBSOCKET.md)** - WebSocket protocol for real-time data streaming
- **[CHANGELOG.md](CHANGELOG.md)** - API version history and breaking changes
- **[strategy.schema.json](strategy.schema.json)** - JSON schema for strategy configuration

## Quick Start

### REST API

Base URL: `http://localhost:8080/api`

Example:
\`\`\`bash
curl http://localhost:8080/api/strategies
\`\`\`

See [REST.md](REST.md) for full API documentation.

### WebSocket

URL: `ws://127.0.0.1:8080/ws`

Example:
\`\`\`javascript
const ws = new WebSocket('ws://127.0.0.1:8080/ws');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
\`\`\`

See [WEBSOCKET.md](WEBSOCKET.md) for protocol details.

## Authentication

All endpoints require JWT authentication. Obtain a token via `/api/auth/login`.

## Rate Limiting

- REST API: 100 requests/minute per IP
- WebSocket: 10 connections per user

---

For implementation details, see [src/api/](../../src/api/).
