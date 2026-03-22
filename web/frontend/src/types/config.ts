// TypeScript types matching the FastAPI / camplayer backend models

export type LayoutId = 1 | 4 | 6 | 7 | 8 | 9 | 10 | 13 | 16

export type PlayState = 0 | 1 | 2 | 3 | 4
export const PlayStateNames: Record<PlayState, string> = {
  0: 'NONE',
  1: 'INIT1',
  2: 'INIT2',
  3: 'PLAYING',
  4: 'BROKEN',
}

export type StreamQuality = 0 | 1 | 2   // LOW | AUTO | HIGH
export type ChangeOver    = 0 | 1 | 2   // NORMAL | PREBUFFER | PREBUFFER_SMOOTH
export type HevcMode      = 0 | 1 | 2 | 3  // OFF | AUTO | FHD | UHD
export type AudioMode     = 0 | 1       // OFF | FULLSCREEN

export interface StreamInfo {
  url: string
  quality_level: number
  codec_name: string
  width: number
  height: number
  framerate: number
  has_audio: boolean
  force_udp: boolean
  valid_url: boolean
  valid_video_windowed: boolean
  valid_video_fullscreen: boolean
  weight: number
  quality: number
}

export interface Channel {
  id: string           // "channel1", "channel2", etc.
  name: string
  streams: StreamInfo[]
  force_udp: boolean
}

export interface Device {
  id: string           // "device1", "device2", etc.
  name: string
  channels: Channel[]
}

export interface WindowPosition {
  x1: number
  y1: number
  x2: number
  y2: number
}

export interface WindowConfig {
  window_idx: number
  device_id: string
  channel_id: string
  display_name: string
  position: WindowPosition
  width: number
  height: number
  layer: number
  visible: boolean
  fullscreen_mode: boolean
  playstate: PlayState
  player_pid: number
  active_stream: StreamInfo | null
}

export interface ScreenConfig {
  screen_idx: number
  layout: LayoutId
  display_idx: number
  displaytime: number   // seconds
  windows: WindowConfig[]
  total_weight: number
}

export interface AdvancedConfig {
  log_level: number
  screen_width: number
  screen_height: number
  buffertime_ms: number
  hardware_check: 0 | 1
  change_over: ChangeOver
  showtime: number
  background_mode: number
  enable_icons: 0 | 1
  stream_watchdog_sec: number
  playtimeout_sec: number
  stream_quality: StreamQuality
  refreshtime_minutes: number
  hevc_mode: HevcMode
  audio_mode: AudioMode
  audio_volume: number
  screen_downscale: number
  video_osd: 0 | 1
}

export interface CamplayerConfig {
  devices: Device[]
  screens: ScreenConfig[]
  advanced: AdvancedConfig
}

// API response wrappers
export interface ApiError {
  detail: string
}

export interface ConfigUpdateResponse {
  success: boolean
  message: string
  restart_required: boolean
}
