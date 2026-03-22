import { useState, useEffect } from 'react'
import { getServerHistory, saveServer, removeServer } from '../utils/tauri-bridge'
import type { ServerInfo } from '../utils/types'

export function useServerHistory() {
  const [history, setHistory] = useState<ServerInfo[]>([])

  useEffect(() => {
    getServerHistory().then(setHistory)
  }, [])

  const addServer = async (server: ServerInfo) => {
    await saveServer(server)
    setHistory(await getServerHistory())
  }

  const deleteServer = async (host: string, port: number) => {
    await removeServer(host, port)
    setHistory(await getServerHistory())
  }

  return { history, addServer, deleteServer }
}
