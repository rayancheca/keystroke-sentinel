import { useCallback, useEffect, useRef, useState } from 'react'
import type { AnomalyResult, KeystrokeBurst, WsMessage } from '../lib/types'

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
const PING_INTERVAL_MS = 15_000
const RECONNECT_DELAY_MS = 2_000

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

interface UseAnomalyStreamOptions {
  userId: string
  sessionId: string
  onScore: (result: AnomalyResult) => void
  onError?: (msg: string) => void
  enabled?: boolean
}

export function useAnomalyStream({
  userId,
  sessionId,
  onScore,
  onError,
  enabled = true,
}: UseAnomalyStreamOptions) {
  const ws = useRef<WebSocket | null>(null)
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [state, setState] = useState<ConnectionState>('disconnected')

  const clearTimers = useCallback(() => {
    if (pingTimer.current) clearInterval(pingTimer.current)
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
  }, [])

  const connect = useCallback(() => {
    if (!enabled || !userId || !sessionId) return
    setState('connecting')
    const url = `${WS_BASE}/ws/${encodeURIComponent(userId)}/${encodeURIComponent(sessionId)}`
    const socket = new WebSocket(url)
    ws.current = socket

    socket.onopen = () => {
      setState('connected')
      pingTimer.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping' }))
        }
      }, PING_INTERVAL_MS)
    }

    socket.onmessage = (ev) => {
      let msg: WsMessage
      try {
        msg = JSON.parse(ev.data as string) as WsMessage
      } catch {
        return
      }
      if (msg.type === 'anomaly_score') onScore(msg.data)
      if (msg.type === 'error') onError?.(msg.message)
    }

    socket.onerror = () => {
      setState('error')
    }

    socket.onclose = () => {
      clearTimers()
      setState('disconnected')
      if (enabled) {
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }
  }, [userId, sessionId, enabled, onScore, onError, clearTimers])

  const disconnect = useCallback(() => {
    clearTimers()
    ws.current?.close()
    ws.current = null
    setState('disconnected')
  }, [clearTimers])

  const sendBurst = useCallback((burst: KeystrokeBurst) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'burst', data: burst }))
    }
  }, [])

  useEffect(() => {
    if (enabled) connect()
    else disconnect()
    return () => {
      clearTimers()
      ws.current?.close()
    }
  }, [enabled, connect, disconnect, clearTimers])

  return { state, sendBurst, disconnect }
}
