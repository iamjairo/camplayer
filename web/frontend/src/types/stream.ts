import type { PlayState } from './config'

export type StreamStatus = 'connecting' | 'playing' | 'error' | 'idle'

export interface ActiveStreamInfo {
  url: string
  codec: string
  resolution: string
  framerate: number
  has_audio: boolean
}

export interface StreamStatusUpdate {
  type: 'stream_status'
  stream_id: string        // e.g. "D01_S01_W01"
  device_id: string
  channel_id: string
  window_idx: number
  screen_idx: number
  display_idx: number
  playstate: PlayState
  playstate_name: string
  active_stream: ActiveStreamInfo | null
  playtime: number         // seconds
  player_pid: number
  updated_at: number       // unix ms
}

export interface HeartbeatMessage {
  type: 'heartbeat'
  timestamp: number
  overall_status: 'healthy' | 'degraded' | 'error'
}

export interface WatchdogAlert {
  type: 'watchdog_alert'
  stream_id: string
  severity: 'warning' | 'error'
  message: string
  action: string
  timestamp: number
}

export interface ScreenChangedMessage {
  type: 'screen_changed'
  display_idx: number
  old_screen_idx: number
  new_screen_idx: number
  timestamp: number
}

export type WsMessage =
  | StreamStatusUpdate
  | HeartbeatMessage
  | WatchdogAlert
  | ScreenChangedMessage

// Keyed by "display_idx:screen_idx:window_idx"
export type StreamStatusMap = Record<string, StreamStatusUpdate>
