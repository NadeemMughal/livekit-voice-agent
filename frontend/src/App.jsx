import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Room, RoomEvent, Track, createLocalAudioTrack } from 'livekit-client'

const AGENT_API    = 'http://localhost:8080'
const TOKEN_SERVER = 'http://localhost:3001'

function ts() {
  return new Date().toLocaleTimeString('en-US', {
    hour12: false, hour: '2-digit', minute: '2-digit',
    second: '2-digit', fractionalSecondDigits: 2,
  })
}

export default function App() {
  const [roomName, setRoomName]       = useState('test-room')
  const [testText, setTestText]       = useState('What time is it?')
  const [connected, setConnected]     = useState(false)
  const [connecting, setConnecting]   = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [recSecs, setRecSecs]         = useState(0)
  const [logs, setLogs]               = useState([])
  const [pipeline, setPipeline]       = useState({ stt: null, llm: null, tts: null })
  const [audioUrl, setAudioUrl]       = useState(null)
  const [busy, setBusy]               = useState(false)

  const roomRef          = useRef(null)
  const logEndRef        = useRef(null)
  const audioRef         = useRef(null)
  const mediaRecRef      = useRef(null)
  const streamRef        = useRef(null)
  const chunksRef        = useRef([])
  const recTimerRef      = useRef(null)
  const prevUrlRef       = useRef(null)
  const agentAudioSids   = useRef(new Set())   // dedup agent audio tracks by SID

  // ── log helpers ───────────────────────────────────────────────────────────
  const addLog = useCallback((msg, type = 'info') => {
    setLogs(s => [...s.slice(-200), { msg: `[${ts()}] ${msg}`, type }])
  }, [])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // ── revoke old blob URLs to avoid memory leaks ────────────────────────────
  useEffect(() => {
    if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current)
    prevUrlRef.current = audioUrl
  }, [audioUrl])

  // ── WebSocket → pipeline events ───────────────────────────────────────────
  useEffect(() => {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//localhost:8080/ws`)

    ws.onopen  = () => addLog('Connected to agent backend', 'success')
    ws.onerror = () => addLog('Backend WS error — is python src/main.py running?', 'error')
    ws.onclose = () => addLog('Backend WS closed', 'warning')

    ws.onmessage = ({ data }) => {
      try {
        const e = JSON.parse(data)
        const { event_type, duration_ms, data: d, message } = e

        if (event_type === 'llm_start') {
          setPipeline({ stt: null, llm: null, tts: null })   // reset on new request
        } else if (event_type === 'stt_end') {
          const text = d?.transcript || message
          setPipeline(p => ({ ...p, stt: { text, ms: duration_ms } }))
          addLog(`STT  "${text}"  ${duration_ms?.toFixed(0)}ms`, 'success')
        } else if (event_type === 'llm_end') {
          const text = d?.response || message
          setPipeline(p => ({ ...p, llm: { text, ms: duration_ms } }))
          addLog(`LLM  "${text}"  ${duration_ms?.toFixed(0)}ms`, 'success')
        } else if (event_type === 'tts_end') {
          setPipeline(p => ({ ...p, tts: { bytes: d?.audio_bytes, ms: duration_ms } }))
          addLog(`TTS  ${d?.audio_bytes} bytes  ${duration_ms?.toFixed(0)}ms`, 'success')
        } else if (event_type === 'error') {
          addLog(`Error: ${message}`, 'error')
        }
      } catch { /* ignore */ }
    }

    return () => { try { ws.close() } catch { /* ignore */ } }
  }, [addLog])

  // ── audio playback helper ─────────────────────────────────────────────────
  function playBlob(blob) {
    const url = URL.createObjectURL(blob)
    setAudioUrl(url)
    requestAnimationFrame(() => {
      if (audioRef.current) {
        audioRef.current.load()
        audioRef.current.play().catch(() => {})
      }
    })
  }

  // ── Test Pipeline  text → LLM → TTS → audio ──────────────────────────────
  async function handleTest() {
    if (!testText.trim() || busy) return
    setBusy(true)
    addLog(`Sending: "${testText}"`, 'info')
    try {
      const res = await fetch(`${AGENT_API}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: testText }),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        addLog(`Test error: ${j.error || res.statusText}`, 'error')
        return
      }
      const blob = await res.blob()
      addLog(`Response received (${blob.size} bytes) — playing`, 'success')
      playBlob(blob)
    } catch (err) {
      addLog(`Test failed: ${err.message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  // ── Voice Recording  mic → STT → LLM → TTS → audio ───────────────────────
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []

      const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg']
        .find(t => MediaRecorder.isTypeSupported(t)) || ''

      const rec = new MediaRecorder(stream, mimeType ? { mimeType } : {})
      mediaRecRef.current = rec

      rec.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      rec.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || 'audio/webm' })
        addLog(`Recording done — ${blob.size} bytes`, 'info')
        await processAudio(blob)
      }

      rec.start(100)
      setIsRecording(true)
      setRecSecs(0)
      recTimerRef.current = setInterval(() => setRecSecs(s => s + 1), 1000)
      addLog('Recording started — speak now', 'info')
    } catch (err) {
      addLog(`Mic error: ${err.message}`, 'error')
    }
  }

  function stopRecording() {
    clearInterval(recTimerRef.current)
    setIsRecording(false)
    if (mediaRecRef.current?.state === 'recording') mediaRecRef.current.stop()
  }

  async function processAudio(blob) {
    setBusy(true)
    addLog('Running pipeline: STT → LLM → TTS...', 'info')
    try {
      const form = new FormData()
      form.append('audio', blob, 'recording.webm')

      const res = await fetch(`${AGENT_API}/process-audio`, { method: 'POST', body: form })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        addLog(`Pipeline error: ${j.error || res.statusText}`, 'error')
        return
      }

      const transcript = res.headers.get('X-Transcript')
      if (transcript) addLog(`You said: "${transcript}"`, 'info')

      const audioBlob = await res.blob()
      addLog(`Agent response (${audioBlob.size} bytes) — playing`, 'success')
      playBlob(audioBlob)
    } catch (err) {
      addLog(`Audio processing failed: ${err.message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  // ── LiveKit Room ──────────────────────────────────────────────────────────
  async function handleConnect() {
    if (!roomName.trim()) { addLog('Enter a room name', 'error'); return }
    setConnecting(true)
    try {
      const res = await fetch(`${TOKEN_SERVER}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room: roomName, identity: `user-${Date.now()}` }),
      })
      if (!res.ok) { addLog(`Token error: ${await res.text()}`, 'error'); return }
      const { token, url } = await res.json()
      addLog(`Token OK — connecting to ${url}`, 'info')

      const room = new Room()

      // ── Register ALL handlers BEFORE connect so we don't miss events ──────
      room.on(RoomEvent.Disconnected,           () => { setConnected(false); addLog('Disconnected', 'warning') })
      room.on(RoomEvent.ParticipantConnected,    p => addLog(`Participant joined: ${p.identity}`, 'success'))
      room.on(RoomEvent.ParticipantDisconnected, p => addLog(`Participant left: ${p.identity}`, 'warning'))

      function attachAgentAudio(track) {
        if (agentAudioSids.current.has(track.sid)) return   // already attached
        agentAudioSids.current.add(track.sid)
        const el = track.attach()
        el.autoplay = true
        document.body.appendChild(el)
        addLog('Agent audio active — you will hear responses', 'success')
      }

      room.on(RoomEvent.TrackSubscribed, (track, _pub, participant) => {
        if (track.kind === Track.Kind.Audio && participant.identity === 'voice-agent') {
          attachAgentAudio(track)
        }
      })
      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach(el => el.remove())
      })
      // ── end pre-connect handlers ─────────────────────────────────────────

      await room.connect(url, token, { autoSubscribe: true })
      roomRef.current = room
      addLog(`Connected to room: ${room.name}`, 'success')

      const track = await createLocalAudioTrack()
      await room.localParticipant.publishTrack(track)
      addLog('Microphone published — speak to interact with the agent', 'success')

      // Handle agent tracks that were published before we joined
      room.remoteParticipants.forEach(p => {
        if (p.identity === 'voice-agent') {
          p.trackPublications.forEach(pub => {
            if (pub.track && pub.track.kind === Track.Kind.Audio) {
              attachAgentAudio(pub.track)
            }
          })
        }
      })

      setConnected(true)
    } catch (err) {
      addLog(`Connect failed: ${err.message}`, 'error')
    } finally {
      setConnecting(false)
    }
  }

  async function handleDisconnect() {
    await roomRef.current?.disconnect()
    roomRef.current = null
    agentAudioSids.current.clear()
    setConnected(false)
    addLog('Disconnected', 'info')
  }

  // ── Pipeline stage component ──────────────────────────────────────────────
  function Stage({ icon, label, color, data }) {
    return (
      <div className={`stage stage-${color}${data ? ' stage-done' : ''}`}>
        <div className="stage-label">{icon} {label}</div>
        {data ? (
          <>
            {data.text  && <div className="stage-text">"{data.text}"</div>}
            {data.bytes && <div className="stage-text">{data.bytes.toLocaleString()} bytes</div>}
            <div className="stage-ms">{data.ms?.toFixed(0)} ms</div>
          </>
        ) : (
          <div className="stage-idle">—</div>
        )}
      </div>
    )
  }

  const hasPipeline = pipeline.stt || pipeline.llm || pipeline.tts

  // ────────────────────────────────────────────────────────────────────────
  return (
    <div className="container">
      <h1>LiveKit Voice Agent</h1>

      {/* Quick Test */}
      <div className="panel">
        <h2>Quick Test <span className="badge">text → LLM → TTS</span></h2>
        <div className="row gap8">
          <input
            className="flex1"
            value={testText}
            onChange={e => setTestText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleTest()}
            placeholder="Type a message and press Enter…"
          />
          <button onClick={handleTest} disabled={busy || !testText.trim()} className="btn-primary">
            {busy ? 'Working…' : 'Send ↩'}
          </button>
        </div>
      </div>

      {/* Voice Recording */}
      <div className="panel">
        <h2>Voice Recording <span className="badge">mic → STT → LLM → TTS</span></h2>
        <div className="row gap8">
          {!isRecording ? (
            <button onClick={startRecording} disabled={busy} className="btn-record">
              Start Recording
            </button>
          ) : (
            <button onClick={stopRecording} className="btn-stop pulse">
              Stop  {recSecs}s
            </button>
          )}
          {busy && !isRecording && <span className="status-label">Processing…</span>}
        </div>
      </div>

      {/* Agent Audio Response */}
      {audioUrl && (
        <div className="panel panel-response">
          <h2>Agent Response</h2>
          <audio ref={audioRef} src={audioUrl} controls className="audio-player" />
        </div>
      )}

      {/* Pipeline Flow */}
      <div className="panel">
        <h2>Pipeline <span className="badge">real-time timing</span></h2>
        {hasPipeline ? (
          <div className="pipeline-flow">
            <Stage icon="🎤" label="STT"  color="green"  data={pipeline.stt} />
            <span className="arrow">→</span>
            <Stage icon="🧠" label="LLM"  color="purple" data={pipeline.llm} />
            <span className="arrow">→</span>
            <Stage icon="🔊" label="TTS"  color="orange" data={pipeline.tts} />
          </div>
        ) : (
          <div className="pipeline-empty">Send text or record voice to see pipeline timing</div>
        )}
      </div>

      {/* LiveKit Room */}
      <div className="panel">
        <h2>LiveKit Room <span className="badge">real-time voice</span></h2>
        <div className="row gap8">
          <input
            className="flex1"
            value={roomName}
            onChange={e => setRoomName(e.target.value)}
            placeholder="room name"
            disabled={connected}
          />
          {!connected ? (
            <button onClick={handleConnect} disabled={connecting} className="btn-primary">
              {connecting ? 'Connecting…' : 'Connect'}
            </button>
          ) : (
            <button onClick={handleDisconnect} className="btn-danger">Disconnect</button>
          )}
        </div>
        {connected && <div className="connected-pill">Connected · {roomName}</div>}
      </div>

      {/* Logs */}
      <div className="panel">
        <div className="log-header">
          <h2 style={{ margin: 0 }}>Logs</h2>
          <button onClick={() => setLogs([])} className="btn-ghost">Clear</button>
        </div>
        <div className="logs">
          {logs.map((l, i) => (
            <div key={i} className={`log-entry log-${l.type}`}>{l.msg}</div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  )
}
