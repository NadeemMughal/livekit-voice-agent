# LiveKit Token Minting Server

This Express.js server generates short-lived JWT tokens for the frontend.

## Quick Start

1. Install dependencies:
```bash
npm install
```

2. Copy `.env.example` to `.env` and fill in your LiveKit credentials:
```
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
LIVEKIT_URL=wss://your_livekit_instance.com
PORT=3001
```

3. Run:
```bash
npm start
```

The server will listen at `http://localhost:3001`.

## Endpoints

### `/health` (GET)
Health check.
```bash
curl http://localhost:3001/health
```

Response:
```json
{"status":"ok"}
```

### `/token` (POST)
Mint an access token for a participant to join a room.

Request:
```bash
curl -X POST http://localhost:3001/token \
  -H "Content-Type: application/json" \
  -d '{"room":"test-room","identity":"user-123"}'
```

Response:
```json
{
  "token": "eyJhbGc...",
  "url": "wss://your_livekit_instance.com"
}
```

## Security Notes

- **Never expose** `LIVEKIT_API_SECRET` in the browser
- This token server should run on a **trusted backend** (not public internet without auth)
- For production, add authentication (OAuth, API keys) before token generation
- Use HTTPS in production
- Consider rate limiting to prevent abuse

## Deployment

### Local Testing
```bash
node index.js
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY index.js .
ENV PORT=3001
EXPOSE 3001
CMD ["node", "index.js"]
```

### Environment Variables (Production)
Set via your deployment platform (Heroku, AWS Lambda, Docker, K8s, etc.):
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `LIVEKIT_URL`
- `PORT`
