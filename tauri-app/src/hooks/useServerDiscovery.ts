import { useState, useEffect } from 'react'
import { discoverServers, onServerDiscovered } from '../utils/tauri-bridge'
import type { ServerInfo } from '../utils/types'

export function useServerDiscovery() {
  const [servers, setServers] = useState<ServerInfo[]>([])
  const [scanning, setScanning] = useState(false)

  const scan = async () => {
    setScanning(true)
    try {
      const found = await discoverServers()
      setServers(found)
    } finally {
      setScanning(false)
    }
  }

  useEffect(() => {
    scan()
    // Also listen for background discovery events
    let unlisten: (() => void) | undefined
    onServerDiscovered((server) => {
      setServers((prev) => {
        const exists = prev.some(
          (s) => s.host === server.host && s.port === server.port
        )
        return exists ? prev : [...prev, server]
      })
    }).then((fn) => {
      unlisten = fn
    })
    return () => {
      unlisten?.()
    }
  }, [])

  return { servers, scanning, rescan: scan }
}
