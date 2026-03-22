import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'
import type { ServerInfo } from './types'

export async function discoverServers(): Promise<ServerInfo[]> {
  return invoke<ServerInfo[]>('discover_servers')
}

export async function getServerHistory(): Promise<ServerInfo[]> {
  return invoke<ServerInfo[]>('get_server_history')
}

export async function saveServer(server: ServerInfo): Promise<void> {
  return invoke('save_server', { server })
}

export async function removeServer(host: string, port: number): Promise<void> {
  return invoke('remove_server', { host, port })
}

export async function testConnection(apiUrl: string): Promise<boolean> {
  return invoke<boolean>('test_connection', { apiUrl })
}

export async function registerShortcuts(): Promise<void> {
  return invoke('register_shortcuts')
}

export async function onServerDiscovered(cb: (server: ServerInfo) => void) {
  return listen<ServerInfo>('server-discovered', (e) => cb(e.payload))
}

export async function onShortcut(cb: (action: string) => void) {
  return listen<string>('shortcut', (e) => cb(e.payload))
}
