import { createContext, useContext, ReactNode } from 'react';
import { createFrontendClient } from '@pipedream/sdk/browser';
import type { FrontendClient } from '@pipedream/sdk/browser';

interface PipedreamContextType {
  client: FrontendClient | null;
}

const PipedreamContext = createContext<PipedreamContextType | undefined>(undefined);

export const usePipedream = () => {
  const context = useContext(PipedreamContext);
  if (!context) {
    throw new Error('usePipedream must be used within a PipedreamProvider');
  }
  return context;
};

interface PipedreamProviderProps {
  children: ReactNode;
  externalUserId: string;
}

export const PipedreamProvider = ({ children, externalUserId }: PipedreamProviderProps) => {
  const client = createFrontendClient({
    environment: import.meta.env.VITE_ENVIRONMENT || 'development',
    projectId: import.meta.env.VITE_PIPEDREAM_PROJECT_ID,
    externalUserId,
    tokenCallback: async () => {
      const response = await fetch('http://localhost:8000/auth/connect-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ external_user_id: externalUserId })
      });

      if (!response.ok) {
        throw new Error('Failed to fetch connect token');
      }

      const data = await response.json();
      return data.token;
    },
  });

  return (
    <PipedreamContext.Provider value={{ client }}>
      {children}
    </PipedreamContext.Provider>
  );
};
