/**
 * go2rtc WebRTC client using the WebSocket signaling API.
 *
 * go2rtc exposes a WebSocket endpoint at /api/ws?src=<stream_id> that
 * performs SDP offer/answer exchange and ICE candidate trickling.
 */

export type WebRTCState = 'connecting' | 'playing' | 'error' | 'closed'

export interface WebRTCHandle {
  pc: RTCPeerConnection
  ws: WebSocket
  close(): void
}

export function connectWebRTC(
  streamId: string,
  videoElement: HTMLVideoElement,
  onStateChange: (state: WebRTCState) => void,
  baseUrl = '',
): WebRTCHandle {
  const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
  })

  pc.addTransceiver('video', { direction: 'recvonly' })
  pc.addTransceiver('audio', { direction: 'recvonly' })

  const wsUrl = `${baseUrl}/go2rtc/api/ws?src=${encodeURIComponent(streamId)}`
  const ws = new WebSocket(wsUrl)

  onStateChange('connecting')

  ws.onmessage = async (e: MessageEvent) => {
    try {
      const msg = JSON.parse(e.data as string)
      if (msg.type === 'answer') {
        await pc.setRemoteDescription(new RTCSessionDescription(msg as RTCSessionDescriptionInit))
      } else if (msg.type === 'candidate' && msg.candidate) {
        await pc.addIceCandidate(new RTCIceCandidate(msg.candidate as RTCIceCandidateInit))
      }
    } catch {
      // ignore parse errors
    }
  }

  ws.onopen = async () => {
    try {
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      ws.send(JSON.stringify({ type: 'offer', sdp: offer.sdp }))
    } catch {
      onStateChange('error')
    }
  }

  ws.onerror = () => onStateChange('error')
  ws.onclose = () => {
    if (pc.connectionState !== 'connected') {
      onStateChange('error')
    }
  }

  pc.ontrack = (e: RTCTrackEvent) => {
    if (e.track.kind === 'video' && e.streams[0]) {
      videoElement.srcObject = e.streams[0]
    }
  }

  pc.onicecandidate = (e: RTCPeerConnectionIceEvent) => {
    if (e.candidate && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'candidate', candidate: e.candidate }))
    }
  }

  pc.onconnectionstatechange = () => {
    switch (pc.connectionState) {
      case 'connected':
        onStateChange('playing')
        break
      case 'failed':
      case 'disconnected':
        onStateChange('error')
        break
      case 'closed':
        onStateChange('closed')
        break
    }
  }

  const close = () => {
    ws.close()
    pc.close()
  }

  return { pc, ws, close }
}
