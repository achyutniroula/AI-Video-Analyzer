'use client';

import VideoUpload from '../components/VideoUpload';
import { useEffect, useState } from 'react';
import { getCurrentUser } from 'aws-amplify/auth';
import '../../lib/aws';
import { useRouter } from 'next/navigation';
import Sidebar from '../components/Sidebar';
import Footer from '../components/Footer';

const font = "'Manrope', sans-serif";

export default function UploadPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => { checkAuth(); }, []);

  async function checkAuth() {
    try {
      await getCurrentUser();
      setIsAuthenticated(true);
    } catch {
      window.location.href = '/login';
    } finally {
      setIsLoading(false);
    }
  }

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite' }} />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', fontFamily: font }}>
      <Sidebar />

      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-10%', right: '-5%', width: '45%', height: '45%', borderRadius: '50%', background: 'rgba(198,198,200,0.025)', filter: 'blur(120px)' }} />
      </div>

      <main style={{ marginLeft: 256, flex: 1, position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', padding: '4rem 2rem' }}>
        <div style={{ width: '100%', maxWidth: 600 }}>
          <p style={{ fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#767578', marginBottom: '1.25rem', textAlign: 'center' }}>New Upload</p>
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(2rem, 4vw, 2.75rem)', color: 'var(--on-surface)', marginBottom: '0.75rem', letterSpacing: '0.03em', textAlign: 'center', filter: 'drop-shadow(0 0 12px var(--header-glow-3)) drop-shadow(0 0 25px var(--header-glow-1))' }}>Import Media</h1>
          <p style={{ color: '#767578', fontFamily: font, fontSize: '0.9rem', fontWeight: 300, marginBottom: '2.5rem', letterSpacing: '0.02em', textAlign: 'center', lineHeight: 1.7 }}>
            Submit your video for AI analysis — detection, segmentation, and narrative generation.
          </p>
          <VideoUpload />
        </div>
        <Footer />
      </main>
    </div>
  );
}
