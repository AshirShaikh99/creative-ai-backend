# Integrating with Next.js Frontend

This guide explains how to integrate the real-time voice agent backend with a Next.js frontend.

## Prerequisites

- Next.js project set up
- LiveKit client SDK installed:
  ```bash
  npm install livekit-client @livekit/components-react
  ```

## Implementation Steps

### 1. Set Up API Client

Create an API client to communicate with the backend:

```typescript
// lib/api.ts
export async function initializeVoiceAgent(userId: string, roomName?: string) {
  const response = await fetch('/api/voice/initialize', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: userId,
      room_name: roomName,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to initialize voice agent');
  }

  return response.json();
}

export async function terminateVoiceAgent(sessionId: string) {
  const response = await fetch(`/api/voice/terminate/${sessionId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('Failed to terminate voice agent');
  }

  return response.json();
}
```

### 2. Set Up API Routes for Backend Communication

Create API routes to proxy requests to your backend:

```typescript
// pages/api/voice/initialize.ts
import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const response = await fetch(`${process.env.BACKEND_URL}/api/audio/initialize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });

    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (error) {
    console.error('Error initializing voice agent:', error);
    return res.status(500).json({ error: 'Failed to initialize voice agent' });
  }
}
```

```typescript
// pages/api/voice/terminate/[sessionId].ts
import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'DELETE') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { sessionId } = req.query;

  try {
    const response = await fetch(`${process.env.BACKEND_URL}/api/audio/terminate/${sessionId}`, {
      method: 'DELETE',
    });

    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (error) {
    console.error('Error terminating voice agent:', error);
    return res.status(500).json({ error: 'Failed to terminate voice agent' });
  }
}
```

### 3. Create a Voice Agent Component

Create a React component to interact with the voice agent:

```tsx
// components/VoiceAgent.tsx
import { useState, useEffect, useCallback } from 'react';
import { Room, RoomEvent, RemoteTrack, LocalTrack, Track, AudioTrack } from 'livekit-client';
import { initializeVoiceAgent, terminateVoiceAgent } from '../lib/api';

interface VoiceAgentProps {
  userId: string;
  onTranscription?: (text: string) => void;
  onResponse?: (text: string) => void;
}

export default function VoiceAgent({ userId, onTranscription, onResponse }: VoiceAgentProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [room, setRoom] = useState<Room | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Connect to voice agent
  const connect = useCallback(async () => {
    try {
      // Initialize session with backend
      const { session_id, room_name, token } = await initializeVoiceAgent(userId);
      setSessionId(session_id);

      // Connect to LiveKit room
      const newRoom = new Room();
      
      // Set up event listeners
      newRoom.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        if (track.kind === Track.Kind.Audio) {
          // Attach audio track to audio element
          const audioElement = new Audio();
          (track as AudioTrack).attach(audioElement);
          audioElement.play();
        }
      });
      
      // Connect to room
      await newRoom.connect(process.env.NEXT_PUBLIC_LIVEKIT_URL as string, token);
      setRoom(newRoom);
      setIsConnected(true);
      
      // Set up WebSocket for receiving transcriptions and responses
      const wsUrl = `${process.env.NEXT_PUBLIC_WEBSOCKET_URL}/api/audio/ws/${session_id}`;
      const socket = new WebSocket(wsUrl);
      
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'transcription' && onTranscription) {
          onTranscription(data.text);
        } else if (data.type === 'response' && onResponse) {
          onResponse(data.text);
        }
      };
      
    } catch (err) {
      setError('Failed to connect to voice agent');
      console.error(err);
    }
  }, [userId, onTranscription, onResponse]);

  // Disconnect from voice agent
  const disconnect = useCallback(async () => {
    if (room) {
      room.disconnect();
    }
    
    if (sessionId) {
      await terminateVoiceAgent(sessionId);
    }
    
    setIsConnected(false);
    setRoom(null);
    setSessionId(null);
  }, [room, sessionId]);

  // Toggle listening state
  const toggleListening = useCallback(async () => {
    if (!room) return;
    
    if (isListening) {
      // Stop recording
      const tracks = room.localParticipant.getTracks();
      tracks.forEach(publication => {
        room.localParticipant.unpublishTrack(publication.track);
      });
      setIsListening(false);
    } else {
      // Start recording
      try {
        const audioTrack = await LocalTrack.createAudioTrack({
          name: 'microphone',
        });
        
        await room.localParticipant.publishTrack(audioTrack);
        setIsListening(true);
      } catch (err) {
        setError('Failed to access microphone');
        console.error(err);
      }
    }
  }, [room, isListening]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (isConnected) {
        disconnect();
      }
    };
  }, [isConnected, disconnect]);

  return (
    <div className="voice-agent">
      {error && <div className="error">{error}</div>}
      
      <div className="controls">
        {!isConnected ? (
          <button onClick={connect}>Connect to Voice Agent</button>
        ) : (
          <>
            <button 
              onClick={toggleListening}
              className={isListening ? 'listening' : ''}
            >
              {isListening ? 'Stop Listening' : 'Start Listening'}
            </button>
            <button onClick={disconnect}>Disconnect</button>
          </>
        )}
      </div>
    </div>
  );
}
```

### 4. Use the Voice Agent Component in a Page

```tsx
// pages/voice-chat.tsx
import { useState } from 'react';
import VoiceAgent from '../components/VoiceAgent';

export default function VoiceChatPage() {
  const [transcription, setTranscription] = useState('');
  const [response, setResponse] = useState('');
  const userId = 'user-' + Math.random().toString(36).substring(2, 9);

  return (
    <div className="container">
      <h1>Voice Chat with AI</h1>
      
      <VoiceAgent 
        userId={userId}
        onTranscription={text => setTranscription(text)}
        onResponse={text => setResponse(text)}
      />
      
      <div className="conversation">
        {transcription && (
          <div className="user-message">
            <strong>You:</strong> {transcription}
          </div>
        )}
        
        {response && (
          <div className="ai-message">
            <strong>AI:</strong> {response}
          </div>
        )}
      </div>
      
      <style jsx>{`
        .container {
          max-width: 800px;
          margin: 0 auto;
          padding: 2rem;
        }
        
        .conversation {
          margin-top: 2rem;
          border: 1px solid #eaeaea;
          border-radius: 10px;
          padding: 1rem;
          min-height: 300px;
        }
        
        .user-message, .ai-message {
          margin-bottom: 1rem;
          padding: 0.5rem;
          border-radius: 5px;
        }
        
        .user-message {
          background-color: #f0f0f0;
        }
        
        .ai-message {
          background-color: #e6f7ff;
        }
      `}</style>
    </div>
  );
}
```

### 5. Environment Setup

Create a `.env.local` file in your Next.js project:

```
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000
```

## Advanced Features

### Push-to-Talk Implementation

For a push-to-talk experience, modify the `VoiceAgent` component:

```tsx
// Inside VoiceAgent.tsx

// Add these functions:
const startTalking = useCallback(async () => {
  if (!room) return;
  
  try {
    const audioTrack = await LocalTrack.createAudioTrack({
      name: 'microphone',
    });
    
    await room.localParticipant.publishTrack(audioTrack);
    setIsListening(true);
  } catch (err) {
    setError('Failed to access microphone');
    console.error(err);
  }
}, [room]);

const stopTalking = useCallback(() => {
  if (!room) return;
  
  const tracks = room.localParticipant.getTracks();
  tracks.forEach(publication => {
    room.localParticipant.unpublishTrack(publication.track);
  });
  setIsListening(false);
}, [room]);

// In the return JSX:
{isConnected && (
  <button 
    onMouseDown={startTalking}
    onMouseUp={stopTalking}
    onTouchStart={startTalking}
    onTouchEnd={stopTalking}
    className={isListening ? 'listening' : ''}
  >
    Hold to Talk
  </button>
)}
```

### Visualizing Audio

Add an audio visualization component:

```tsx
// components/AudioVisualizer.tsx
import { useRef, useEffect } from 'react';

interface AudioVisualizerProps {
  isListening: boolean;
}

export default function AudioVisualizer({ isListening }: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);
  
  useEffect(() => {
    if (!isListening) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      return;
    }
    
    let audioContext: AudioContext;
    let analyser: AnalyserNode;
    let microphone: MediaStreamAudioSourceNode;
    
    async function setupAudio() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioContext = new AudioContext();
        analyser = audioContext.createAnalyser();
        analyserRef.current = analyser;
        analyser.fftSize = 256;
        
        microphone = audioContext.createMediaStreamSource(stream);
        microphone.connect(analyser);
        
        visualize();
      } catch (err) {
        console.error('Error accessing microphone:', err);
      }
    }
    
    function visualize() {
      if (!canvasRef.current || !analyserRef.current) return;
      
      const canvas = canvasRef.current;
      const canvasCtx = canvas.getContext('2d');
      if (!canvasCtx) return;
      
      const WIDTH = canvas.width;
      const HEIGHT = canvas.height;
      
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      
      canvasCtx.clearRect(0, 0, WIDTH, HEIGHT);
      
      function draw() {
        if (!analyserRef.current) return;
        
        animationRef.current = requestAnimationFrame(draw);
        
        analyserRef.current.getByteFrequencyData(dataArray);
        
        canvasCtx.fillStyle = 'rgb(0, 0, 0)';
        canvasCtx.fillRect(0, 0, WIDTH, HEIGHT);
        
        const barWidth = (WIDTH / bufferLength) * 2.5;
        let barHeight;
        let x = 0;
        
        for(let i = 0; i < bufferLength; i++) {
          barHeight = dataArray[i] / 2;
          
          canvasCtx.fillStyle = `rgb(50, ${barHeight + 100}, 50)`;
          canvasCtx.fillRect(x, HEIGHT - barHeight, barWidth, barHeight);
          
          x += barWidth + 1;
        }
      }
      
      draw();
    }
    
    setupAudio();
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isListening]);
  
  return (
    <canvas ref={canvasRef} width="300" height="50" className="audio-visualizer" />
  );
}
```

Then use it in your `VoiceAgent` component:

```tsx
// Inside VoiceAgent.tsx return JSX:
{isConnected && (
  <div className="visualizer-container">
    <AudioVisualizer isListening={isListening} />
  </div>
)}
```

## Troubleshooting

### Common Issues

1. **Connection Issues**
   - Ensure LiveKit server is accessible from your client
   - Check that your tokens are properly signed and not expired

2. **Audio Not Working**
   - Verify browser permissions are granted for microphone access
   - Check that audio tracks are properly published and subscribed

3. **High Latency**
   - Optimize chunk size for audio transmission
   - Consider using a LiveKit server geographically closer to your users

4. **Microphone Access Denied**
   - Make sure to request microphone access in response to a user gesture
   - Handle permissions errors gracefully with user-friendly messages
