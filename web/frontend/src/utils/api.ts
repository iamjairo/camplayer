import type { CamplayerConfig, ConfigUpdateResponse } from '../types/config'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

// ─── Config ──────────────────────────────────────────────────────────────────

export function fetchConfig(): Promise<CamplayerConfig> {
  return request<CamplayerConfig>('/config')
}

export function putConfig(config: CamplayerConfig): Promise<ConfigUpdateResponse> {
  return request<ConfigUpdateResponse>('/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  })
}

// ─── Layout control ──────────────────────────────────────────────────────────

export function postNextScreen(displayIdx: number): Promise<void> {
  return request<void>(`/layout/next?display=${displayIdx}`, { method: 'POST' })
}

export function postPrevScreen(displayIdx: number): Promise<void> {
  return request<void>(`/layout/prev?display=${displayIdx}`, { method: 'POST' })
}

export function postSetScreen(displayIdx: number, screenIdx: number): Promise<void> {
  return request<void>(`/layout/screen?display=${displayIdx}&screen=${screenIdx}`, {
    method: 'POST',
  })
}

// ─── Stream info ─────────────────────────────────────────────────────────────

export function fetchStreamStatuses() {
  return request<Record<string, unknown>>('/streams/status')
}

// ─── SWR fetcher (key is the path, value comes from fetchConfig) ─────────────

export const swrFetcher = (_key: string) => fetchConfig()
