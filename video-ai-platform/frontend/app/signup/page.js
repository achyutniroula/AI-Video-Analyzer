'use client';

import { useState } from 'react';
import { signUp } from 'aws-amplify/auth';
import '../../lib/aws';
import Link from 'next/link';
import { GlowCard } from '@/components/ui/spotlight-card';
import { GlassButton } from '@/components/ui/liquid-glass-button';

const font = "'Manrope', sans-serif";

const inputStyle = {
  width: '100%',
  background: 'var(--input-bg)',
  border: '1px solid rgba(72,72,75,0.35)',
  borderRadius: '4px',
  padding: '0.875rem 1rem 0.875rem 2.75rem',
  color: '#e7e5e8',
  fontSize: '0.9rem',
  fontWeight: 300,
  outline: 'none',
  transition: 'border-color 0.2s',
  fontFamily: font,
};

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSignup(e) {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');
    try {
      const username = email.split('@')[0] + Date.now();
      await signUp({
        username,
        password,
        options: {
          userAttributes: { email },
          autoSignIn: true,
        },
      });
      setMessage('success:Signup successful! Check your email for the confirmation code.');
      setTimeout(() => {
        window.location.href = `/confirm?email=${encodeURIComponent(email)}&username=${encodeURIComponent(username)}`;
      }, 2000);
    } catch (err) {
      setMessage('error:' + (err.message || 'Signup failed'));
    } finally {
      setIsLoading(false);
    }
  }

  const isSuccess = message.startsWith('success:');
  const displayMessage = message.replace(/^(success|error):/, '');

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', fontFamily: font }}>

      <div style={{ position: 'fixed', top: '20%', left: '50%', transform: 'translateX(-50%)', width: 500, height: 500, background: 'radial-gradient(circle, rgba(198,198,200,0.03) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div style={{ width: '100%', maxWidth: 420 }}>
        {/* Wordmark */}
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.625rem', marginBottom: '2rem' }}>
            <div style={{ width: 26, height: 26, background: 'linear-gradient(135deg, #c6c6c8, #454749)', borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#0e0e0f', fontVariationSettings: "'FILL' 1, 'wght' 400" }}>camera</span>
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 300, letterSpacing: '0.2em', textTransform: 'uppercase', color: '#767578' }}>Video Understanding Platform</span>
          </div>
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: '2.5rem', color: '#e7e5e8', letterSpacing: '0.04em', marginBottom: '0.5rem' }}>Create Account</h1>
          <p style={{ color: '#767578', fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.05em' }}>Start analyzing videos with AI</p>
        </div>

        <GlowCard className="p-8">
          <form onSubmit={handleSignup} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {message && (
              <div style={{ background: isSuccess ? 'rgba(52,211,153,0.05)' : 'rgba(238,125,119,0.06)', border: `1px solid ${isSuccess ? 'rgba(52,211,153,0.2)' : 'rgba(238,125,119,0.2)'}`, borderRadius: 4, padding: '0.75rem 1rem', color: isSuccess ? '#6ee7b7' : '#ee7d77', fontSize: '0.825rem', fontWeight: 300, display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: font }}>
                {isSuccess && <span className="material-symbols-outlined" style={{ fontSize: 15 }}>check_circle</span>}
                {displayMessage}
              </div>
            )}

            <div style={{ position: 'relative' }}>
              <span className="material-symbols-outlined" style={{ position: 'absolute', left: '0.875rem', top: '50%', transform: 'translateY(-50%)', fontSize: 16, color: '#48484b', pointerEvents: 'none' }}>mail</span>
              <input type="email" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)}
                required disabled={isLoading} style={inputStyle}
                onFocus={e => e.target.style.borderColor = 'rgba(198,198,200,0.35)'}
                onBlur={e => e.target.style.borderColor = 'rgba(72,72,75,0.35)'} />
            </div>

            <div style={{ position: 'relative' }}>
              <span className="material-symbols-outlined" style={{ position: 'absolute', left: '0.875rem', top: '50%', transform: 'translateY(-50%)', fontSize: 16, color: '#48484b', pointerEvents: 'none' }}>lock</span>
              <input type="password" placeholder="Password (min 8 chars)" value={password} onChange={e => setPassword(e.target.value)}
                required minLength={8} disabled={isLoading} style={inputStyle}
                onFocus={e => e.target.style.borderColor = 'rgba(198,198,200,0.35)'}
                onBlur={e => e.target.style.borderColor = 'rgba(72,72,75,0.35)'} />
            </div>

            <div style={{ marginTop: '0.375rem' }}>
              <GlassButton type="submit" disabled={isLoading} style={{ width: '100%' }}>
                {isLoading ? 'Creating account...' : 'Create Account'}
              </GlassButton>
            </div>
          </form>
        </GlowCard>

        <p style={{ textAlign: 'center', marginTop: '1.75rem', color: '#767578', fontSize: '0.85rem', fontWeight: 300, letterSpacing: '0.03em', fontFamily: font }}>
          Already have an account?{' '}
          <Link href="/login" style={{ color: '#acaaae', fontWeight: 300 }}>Sign in</Link>
        </p>
      </div>

      {/* Footer */}
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '1rem 3rem', borderTop: '1px solid rgba(72,72,75,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', pointerEvents: 'none' }}>
        <p style={{ color: '#2b2c2f', fontSize: '0.68rem', fontWeight: 300, letterSpacing: '0.12em', fontFamily: font }}>Developed by Achyut and Shoaib</p>
        <p style={{ color: '#1e1f22', fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.1em', textTransform: 'uppercase', fontFamily: font }}>COSC 4896</p>
      </div>
    </div>
  );
}
