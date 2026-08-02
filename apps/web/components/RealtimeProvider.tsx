"use client";

import { useEffect, useState, createContext, useContext } from 'react';
import { io, Socket } from 'socket.io-client';

const RealtimeContext = createContext<Socket | null>(null);

export function useRealtime() {
  return useContext(RealtimeContext);
}

export default function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const [socket, setSocket] = useState<Socket | null>(null);

  useEffect(() => {
    const socketUrl = process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:3001';
    const s = io(socketUrl);
    
    setSocket(s);
    
    return () => {
      s.disconnect();
    };
  }, []);

  return (
    <RealtimeContext.Provider value={socket}>
      {children}
    </RealtimeContext.Provider>
  );
}
