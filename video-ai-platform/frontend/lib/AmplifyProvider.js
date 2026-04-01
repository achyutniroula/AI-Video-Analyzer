'use client';

/**
 * Client-side Amplify Configuration
 * This file configures Amplify on the client side for Next.js App Router
 */

import { Amplify } from 'aws-amplify';

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'us-east-2_EXhaj2knX',
      userPoolClientId: '53322vb71fe8qeicbl5096fugn',
      region: 'us-east-2',
      loginWith: {
        email: true,
      },
    }
  }
};

// Configure immediately at module load time — not in useEffect
// This prevents the race condition where page effects run before Amplify is configured
Amplify.configure(amplifyConfig, { ssr: false });

export function AmplifyProvider({ children }) {
  return <>{children}</>;
}

// Also export for direct use
export const configureAmplify = () => {
  Amplify.configure(amplifyConfig, { ssr: false });
};