'use client';

import { useState, useEffect } from 'react';
import { confirmSignUp, resendSignUpCode } from 'aws-amplify/auth';
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

export default function ConfirmPage() {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [code, setCode] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const emailParam = params.get('email');
    const usernameParam = params.get('username');
    if (emailParam) setEmail(decodeURIComponent(emailParam));
    if (usernameParam) setUsername(decodeURIComponent(usernameParam));
  }, []);

  async function handleConfirm(e) {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');
    const confirmUsername = username || email;
    try {
      const { isSignUpComplete, nextStep } = await confirmSignUp({ username: confirmUsername, confirmationCode: code });
      if (isSignUpComplete) {
        setMessage('success:Email confirmed! Redirecting to login...');
        setTimeout(() => { window.location.href = '/login'; }, 2000);
      } else {
        setMessage(`info:Confirmation step: ${nextStep.signUpStep}`);
      }
    } catch (err) {
      if (err.name === 'CodeMismatchException') setMessage('error:Invalid confirmation code. Please try again.');
      else if (err.name === 'ExpiredCodeException') setMessage('error:Code expired. Please request a new one.');
      else if (err.name === 'AliasExistsException') {
        setMessage('success:Email already confirmed. Redirecting to login...');
        setTimeout(() => { window.location.href = '/login'; }, 2000);
      } else setMessage('error:' + (err.message || 'Confirmation failed'));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleResendCode() {
    if (!email) { setMessage('error:Please enter your email address.'); return; }
    setIsLoading(true);
    setMessage('');
    const resendUsername = username || email;
    try {
      await resendSignUpCode({ username: resendUsername });
      setMessage('success:New confirmation code sent! Check your email.');
    } catch (err) {
      if (err.name === 'LimitExceededException') setMessage('error:Too many requests. Please wait before requesting a new code.');
      else setMessage('error:' + (err.message || 'Failed to resend code'));
    } finally {
      setIsLoading(false);
    }
  }

  const isSuccess = message.startsWith('success:');
  const displayMessage = message.replace(/^(success|error|info):/, '');

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', fontFamily: font }}>

      <div style={{ position: 'fixed', top: '20%', left: '50%', transform: 'translateX(-50%)', width: 500, height: 500, background: 'radial-gradient(circle, rgba(198,198,200,0.03) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div style={{ width: '100%', maxWidth: 420 }}>
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.625rem', marginBottom: '2rem' }}>
            <div style={{ width: 26, height: 26, background: 'linear-gradient(135deg, #c6c6c8, #454749)', borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#0e0e0f', fontVariationSettings: "'FILL' 1, 'wght' 400" }}>camera</span>
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 300, letterSpacing: '0.2em', textTransform: 'uppercase', color: '#767578' }}>Video Understanding Platform</span>
          </div>
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: '2.5rem', color: '#e7e5e8', letterSpacing: '0.04em', marginBottom: '0.5rem' }}>Confirm Email</h1>
          <p style={{ color: '#767578', fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.05em' }}>Enter the 6-digit code sent to your email</p>
        </div>

        <GlowCard className="p-8">
          <form onSubmit={handleConfirm} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {message && (
              <div style={{ background: isSuccess ? 'rgba(52,211,153,0.05)' : 'rgba(238,125,119,0.06)', border: `1px solid ${isSuccess ? 'rgba(52,211,153,0.2)' : 'rgba(238,125,119,0.2)'}`, borderRadius: 4, padding: '0.75rem 1rem', color: isSuccess ? '#6ee7b7' : '#ee7d77', fontSize: '0.825rem', fontWeight: 300, display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: font }}>
                {isSuccess && <span className="material-symbols-outlined" style={{ fontSize: 15 }}>check_circle</span>}
                {displayMessage}
              </div>
            )}

            <div style={{ position: 'relative' }}>
              <span className="material-symbols-outlined" style={{ position: 'absolute', left: '0.875rem', top: '50%', transform: 'translateY(-50%)', fontSize: 16, color: '#48484b', pointerEvents: 'none' }}>mail</span>
              <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)}
                required disabled={isLoading} style={inputStyle}
                onFocus={e => e.target.style.borderColor = 'rgba(198,198,200,0.35)'}
                onBlur={e => e.target.style.borderColor = 'rgba(72,72,75,0.35)'} />
            </div>

            <div style={{ position: 'relative' }}>
              <span className="material-symbols-outlined" style={{ position: 'absolute', left: '0.875rem', top: '50%', transform: 'translateY(-50%)', fontSize: 16, color: '#48484b', pointerEvents: 'none' }}>tag</span>
              <input type="text" placeholder="Confirmation Code" value={code} onChange={e => setCode(e.target.value)}
                required maxLength={6} disabled={isLoading}
                style={{ ...inputStyle, letterSpacing: '0.4em', fontSize: '1.1rem', textAlign: 'center', paddingLeft: '1rem' }}
                onFocus={e => e.target.style.borderColor = 'rgba(198,198,200,0.35)'}
                onBlur={e => e.target.style.borderColor = 'rgba(72,72,75,0.35)'} />
            </div>

            <div style={{ marginTop: '0.375rem' }}>
              <GlassButton type="submit" disabled={isLoading} style={{ width: '100%' }}>
                {isLoading ? 'Confirming...' : 'Confirm Email'}
              </GlassButton>
            </div>
          </form>

          <div style={{ marginTop: '0.75rem' }}>
            <GlassButton onClick={handleResendCode} disabled={isLoading} variant="secondary" style={{ width: '100%' }}>
              Resend Code
            </GlassButton>
          </div>
        </GlowCard>

        <p style={{ textAlign: 'center', marginTop: '1.75rem' }}>
          <Link href="/login" style={{ color: '#48484b', fontSize: '0.8rem', fontWeight: 300, fontFamily: font, letterSpacing: '0.05em' }}>← Back to sign in</Link>
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
