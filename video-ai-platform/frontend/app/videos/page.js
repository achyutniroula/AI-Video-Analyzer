'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from 'aws-amplify/auth';
import VideoList from '../components/VideoList';
import Sidebar from '../components/Sidebar';
import Footer from '../components/Footer';

const font = "'Manrope', sans-serif";

export default function VideosPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => { checkAuth(); }, []);

  async function checkAuth() {
    try {
      await getCurrentUser();
      setAuthenticated(true);
    } catch {
      router.push('/login');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite' }} />
      </div>
    );
  }

  if (!authenticated) return null;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', fontFamily: font }}>
      <Sidebar />

      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-10%', right: '-5%', width: '45%', height: '45%', borderRadius: '50%', background: 'rgba(198,198,200,0.025)', filter: 'blur(120px)' }} />
      </div>

      <main style={{ marginLeft: 256, flex: 1, position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column' }}>
        <VideoList />
        <Footer />
      </main>
    </div>
  );
}
