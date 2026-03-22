import { useState } from 'react'
import { ServerSelector } from './components/ServerSelector'
import { ConnectedApp } from './components/ConnectedApp'
import type { ServerInfo } from './utils/types'

export default function App() {
  const [server, setServer] = useState<ServerInfo | null>(null)

  if (!server) {
    return <ServerSelector onConnect={setServer} />
  }

  return <ConnectedApp server={server} onDisconnect={() => setServer(null)} />
}
