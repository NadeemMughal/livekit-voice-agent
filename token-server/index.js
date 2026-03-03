#!/usr/bin/env node
/**
 * Token Minting Server for LiveKit Voice Agent
 *
 * Generates short-lived access tokens for browser clients.
 * Set environment: LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL
 */

const express = require('express')
const cors = require('cors')
const { AccessToken } = require('livekit-server-sdk')
require('dotenv').config()

const app = express()
app.use(cors())
app.use(express.json())

const { LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL } = process.env

if (!LIVEKIT_API_KEY || !LIVEKIT_API_SECRET || !LIVEKIT_URL) {
  console.error('Missing required env vars: LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL')
  process.exit(1)
}

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' })
})

// Mint token endpoint
app.post('/token', (req, res) => {
  try {
    const { room, identity } = req.body
    if (!room || !identity) {
      return res.status(400).json({ error: 'room and identity required' })
    }

    const token = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
      identity,
      name: `User ${Date.now()}`,
    })

    // livekit-server-sdk uses addGrant for grants
    token.addGrant({ room, roomJoin: true, canPublish: true, canSubscribe: true })

    const jwt = token.toJwt()
    res.json({ token: jwt, url: LIVEKIT_URL })
  } catch (err) {
    console.error('Token generation error:', err)
    res.status(500).json({ error: err.message })
  }
})

const PORT = process.env.PORT || 3001
app.listen(PORT, () => {
  console.log(`Token server listening on http://localhost:${PORT}`)
  console.log(`LiveKit URL: ${LIVEKIT_URL}`)
})
