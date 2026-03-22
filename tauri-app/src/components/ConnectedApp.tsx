import { useEffect } from 'react'
import { onShortcut, registerShortcuts } from '../utils/tauri-bridge'
import type { ServerInfo } from '../utils/types'

interface Props {
  server: ServerInfo
  onDisconnect: () => void
}

export function ConnectedApp({ server, onDisconnect }: Props) {
  // The server's web UI is loaded via iframe.
  // Shortcuts are handled natively and forwarded as postMessage to the iframe.
  useEffect(() => {
    registerShortcuts()
    let unlisten: (() => void) | undefined
    onShortcut((action) => {
      const iframe = document.getElementById('camplayer-frame') as HTMLIFrameElement
      iframe?.contentWindow?.postMessage({ type: 'shortcut', action }, '*')
      if (action === 'quit') onDisconnect()
    }).then((fn) => {
      unlisten = fn
    })
    return () => {
      unlisten?.()
    }
  }, [onDisconnect])

  return (
    <div className="w-full h-screen bg-black">
      <iframe
        id="camplayer-frame"
        src={server.api_url}
        className="w-full h-full border-0"
        title="Camplayer"
        allow="camera; microphone; autoplay"
      />
    </div>
  )
}
