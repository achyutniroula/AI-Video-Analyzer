'use client';

import { useState, useEffect } from 'react';
import { signIn, getCurrentUser } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { GlassButton } from '@/components/ui/liquid-glass-button';

const font = "'Manrope', sans-serif";

const inputStyle = {
  width: '100%',
  background: 'var(--input-bg)',
  border: '1px solid rgba(72,72,75,0.35)',
  borderRadius: '4px',
  padding: '0.875rem 1rem 0.875rem 2.75rem',
  color: 'var(--on-surface)',
  fontSize: '0.9rem',
  fontWeight: 300,
  outline: 'none',
  transition: 'all 0.3s cubic-bezier(0.2,0,0,1)',
  fontFamily: font,
  boxShadow: 'inset 0 0 15px rgba(100, 200, 255, 0.03)',
};

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const router = useRouter();

  useEffect(() => { checkIfLoggedIn(); }, []);

  async function checkIfLoggedIn() {
    try {
      await getCurrentUser();
      router.replace('/dashboard');
    } catch {
      setCheckingAuth(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await signIn({ username: email, password });
      if (result.isSignedIn) {
        router.replace('/dashboard');
      } else {
        setError('Sign in incomplete. Please try again.');
      }
    } catch (err) {
      setError(err.message || 'Failed to sign in');
    } finally {
      setLoading(false);
    }
  }

  if (checkingAuth) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite' }} />
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', fontFamily: font }}>

      {/* Background ambient */}
      <div style={{ position: 'fixed', top: '20%', left: '50%', transform: 'translateX(-50%)', width: 500, height: 500, background: 'radial-gradient(circle, rgba(198,198,200,0.03) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div style={{ width: '100%', maxWidth: 420 }}>
        {/* Wordmark */}
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.625rem', marginBottom: '2rem' }}>
            <div style={{ width: 26, height: 26, background: 'linear-gradient(135deg, var(--primary), var(--outline))', borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--bg)', fontVariationSettings: "'FILL' 1, 'wght' 500" }}>lens</span>
            </div>
            <div>
              <span style={{ fontSize: '0.875rem', fontWeight: 200, letterSpacing: '0.15em', color: 'var(--on-surface)' }}>VisionFlow</span>
            </div>
          </div>
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: '2.5rem', color: 'var(--on-surface)', letterSpacing: '0.04em', marginBottom: '0.5rem' }}>Welcome Back</h1>
          <p style={{ color: 'var(--on-muted)', fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.05em' }}>Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {error && (
            <div style={{ background: 'rgba(238,125,119,0.06)', border: '1px solid rgba(238,125,119,0.2)', borderRadius: 4, padding: '0.75rem 1rem', color: '#ee7d77', fontSize: '0.825rem', fontWeight: 300, letterSpacing: '0.02em', fontFamily: font, boxShadow: '0 0 15px rgba(238,125,119,0.1), inset 0 0 15px rgba(238,125,119,0.05)', transition: 'all 0.3s ease' }}>
              {error}
            </div>
          )}

          <div style={{ position: 'relative' }}>
            <span className="material-symbols-outlined" style={{ position: 'absolute', left: '0.875rem', top: '50%', transform: 'translateY(-50%)', fontSize: 16, color: 'var(--outline-dim)', pointerEvents: 'none' }}>mail</span>
            <input type="email" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)}
              required disabled={loading} style={inputStyle}
              onFocus={e => {
                e.target.style.borderColor = 'rgba(100, 200, 255, 0.6)';
                e.target.style.boxShadow = 'inset 0 0 20px rgba(100, 200, 255, 0.1), 0 0 20px rgba(100, 200, 255, 0.15)';
              }}
              onBlur={e => {
                e.target.style.borderColor = 'rgba(72,72,75,0.35)';
                e.target.style.boxShadow = 'inset 0 0 15px rgba(100, 200, 255, 0.03)';
              }} />
          </div>

          <div style={{ position: 'relative' }}>
            <span className="material-symbols-outlined" style={{ position: 'absolute', left: '0.875rem', top: '50%', transform: 'translateY(-50%)', fontSize: 16, color: 'var(--outline-dim)', pointerEvents: 'none' }}>lock</span>
            <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)}
              required disabled={loading} style={inputStyle}
              onFocus={e => {
                e.target.style.borderColor = 'rgba(198, 119, 221, 0.6)';
                e.target.style.boxShadow = 'inset 0 0 20px rgba(198, 119, 221, 0.1), 0 0 20px rgba(198, 119, 221, 0.15)';
              }}
              onBlur={e => {
                e.target.style.borderColor = 'rgba(72,72,75,0.35)';
                e.target.style.boxShadow = 'inset 0 0 15px rgba(100, 200, 255, 0.03)';
              }} />
          </div>

          <div style={{ marginTop: '0.375rem' }}>
            <GlassButton type="submit" disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Signing in...' : 'Sign In'}
            </GlassButton>
          </div>
        </form>

        <p style={{ textAlign: 'center', marginTop: '1.75rem', color: 'var(--on-muted)', fontSize: '0.85rem', fontWeight: 300, letterSpacing: '0.03em', fontFamily: font }}>
          Don&apos;t have an account?{' '}
          <Link href="/signup" style={{ color: 'var(--primary)', fontWeight: 300 }}>Create one</Link>
        </p>
        <p style={{ textAlign: 'center', marginTop: '0.75rem' }}>
          <Link href="/" style={{ color: 'var(--outline-dim)', fontSize: '0.8rem', fontWeight: 300, fontFamily: font, letterSpacing: '0.05em' }}>← Back to home</Link>
        </p>
      </div>

      {/* Footer */}
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '1rem 3rem', borderTop: '1px solid rgba(72,72,75,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', pointerEvents: 'none' }}>
        <p style={{ color: 'var(--on-muted)', fontSize: '0.68rem', fontWeight: 300, letterSpacing: '0.12em', fontFamily: font }}>Developed by Achyut and Shoaib</p>
        <p style={{ color: 'var(--outline)', fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.1em', textTransform: 'uppercase', fontFamily: font }}>COSC 4896</p>
      </div>
    </div>
  );
}
