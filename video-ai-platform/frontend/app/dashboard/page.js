'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from 'aws-amplify/auth';
import { GlowCard } from '@/components/ui/spotlight-card';
import Sidebar from '../components/Sidebar';
import Footer from '../components/Footer';

const font = "'Manrope', sans-serif";

const cards = [
  { icon: 'upload', label: 'New Upload', title: 'Upload Video', desc: 'Submit a new video for AI analysis', href: '/upload', cta: 'Import Media' },
  { icon: 'video_library', label: 'Library', title: 'My Videos', desc: 'Browse and review processed results', href: '/videos', cta: 'Open Library' },
  { icon: 'monitoring', label: 'System', title: 'System Logs', desc: 'Full worker output and processing logs for every video', href: '/system', cta: 'View Logs' },
];

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { checkUser(); }, []);

  async function checkUser() {
    try {
      const userData = await getCurrentUser();
      setUser(userData);
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

  if (!user) return null;

  const username = user?.username || user?.signInDetails?.loginId?.split('@')[0] || 'there';

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', fontFamily: font }}>
      <Sidebar />

      {/* Background ambient */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-10%', right: '-5%', width: '45%', height: '45%', borderRadius: '50%', background: 'rgba(198,198,200,0.025)', filter: 'blur(120px)' }} />
      </div>

      <main style={{ marginLeft: 256, flex: 1, padding: '3.5rem 3rem', position: 'relative', zIndex: 1 }}>

        {/* Section label */}
        <p style={{ fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#767578', marginBottom: '1.25rem' }}>Workspace</p>

        {/* Welcome */}
        <div style={{ marginBottom: '4rem' }}>
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(2.5rem, 5vw, 4rem)', lineHeight: 1.05, letterSpacing: '0.02em', color: 'var(--on-surface)', marginBottom: '0.75rem', filter: 'drop-shadow(0 0 14px var(--header-glow-1)) drop-shadow(0 0 28px var(--header-glow-2))' }}>
            Welcome Back
          </h1>
          <p style={{ fontFamily: font, color: '#767578', fontSize: '0.95rem', fontWeight: 300, letterSpacing: '0.03em' }}>
            Good to see you, {username}. What would you like to do today?
          </p>
        </div>

        {/* Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '3rem' }}>
          {cards.map((card, i) => (
            <GlowCard
              key={i}
              onClick={() => router.push(card.href)}
              style={{ cursor: 'pointer', transition: 'transform 0.3s cubic-bezier(0.2,0,0,1)' }}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-4px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
            >
              {/* Thumbnail */}
              <div style={{ height: 148, overflow: 'hidden', borderRadius: '10px 10px 0 0', position: 'relative', background: '#0e0e0f' }}>
                {i === 0 && (
                  <svg width="100%" height="100%" viewBox="0 0 280 148" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id="uploadGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style={{stopColor:'#1a1a1c',stopOpacity:1}} />
                        <stop offset="100%" style={{stopColor:'#2a2a2e',stopOpacity:1}} />
                      </linearGradient>
                    </defs>
                    <rect width="280" height="148" fill="url(#uploadGrad)"/>
                    <g transform="translate(140,74)">
                      <circle cx="0" cy="0" r="25" fill="none" stroke="#c6c6c8" strokeWidth="1" opacity="0.3"/>
                      <path d="M -15 -10 L 0 5 L 15 -10" stroke="#c6c6c8" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                        <animateTransform attributeName="transform" type="translate" values="0,0;0,-5;0,0" dur="2s" repeatCount="indefinite"/>
                      </path>
                      <rect x="-8" y="8" width="16" height="2" fill="#767578" rx="1"/>
                      <rect x="-8" y="12" width="12" height="2" fill="#767578" rx="1"/>
                      <animate attributeName="opacity" values="0.7;1;0.7" dur="3s" repeatCount="indefinite"/>
                    </g>
                  </svg>
                )}
                {i === 1 && (
                  <svg width="100%" height="100%" viewBox="0 0 280 148" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id="videoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style={{stopColor:'#1a1a1c',stopOpacity:1}} />
                        <stop offset="100%" style={{stopColor:'#2a2a2e',stopOpacity:1}} />
                      </linearGradient>
                    </defs>
                    <rect width="280" height="148" fill="url(#videoGrad)"/>
                    <g transform="translate(140,74)">
                      <rect x="-20" y="-15" width="40" height="30" fill="none" stroke="#c6c6c8" strokeWidth="1" rx="2"/>
                      <polygon points="-10,-8 0,0 -10,8" fill="#c6c6c8">
                        <animate attributeName="opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/>
                      </polygon>
                      <line x1="-5" y1="10" x2="15" y2="10" stroke="#767578" strokeWidth="2" strokeLinecap="round">
                        <animate attributeName="stroke-dasharray" values="0,20;20,0" dur="1.5s" repeatCount="indefinite"/>
                      </line>
                      <circle cx="8" cy="-5" r="1" fill="#c6c6c8" opacity="0.8">
                        <animate attributeName="cy" values="-5;-3;-5" dur="2s" repeatCount="indefinite"/>
                      </circle>
                      <circle cx="12" cy="-5" r="1" fill="#c6c6c8" opacity="0.6">
                        <animate attributeName="cy" values="-5;-4;-5" dur="2.5s" repeatCount="indefinite"/>
                      </circle>
                    </g>
                  </svg>
                )}
                {i === 2 && (
                  <svg width="100%" height="100%" viewBox="0 0 280 148" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id="logsGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style={{stopColor:'#1a1a1c',stopOpacity:1}} />
                        <stop offset="100%" style={{stopColor:'#2a2a2e',stopOpacity:1}} />
                      </linearGradient>
                    </defs>
                    <rect width="280" height="148" fill="url(#logsGrad)"/>
                    <g transform="translate(140,74)">
                      <rect x="-25" y="-20" width="50" height="40" fill="none" stroke="#c6c6c8" strokeWidth="1" rx="2"/>
                      <line x1="-20" y1="-10" x2="20" y2="-10" stroke="#767578" strokeWidth="1"/>
                      <line x1="-20" y1="-5" x2="15" y2="-5" stroke="#767578" strokeWidth="1"/>
                      <line x1="-20" y1="0" x2="10" y2="0" stroke="#767578" strokeWidth="1"/>
                      <line x1="-20" y1="5" x2="18" y2="5" stroke="#767578" strokeWidth="1"/>
                      <line x1="-20" y1="10" x2="12" y2="10" stroke="#767578" strokeWidth="1"/>
                      <line x1="-20" y1="15" x2="16" y2="15" stroke="#767578" strokeWidth="1">
                        <animate attributeName="x2" values="16;20;16" dur="1s" repeatCount="indefinite"/>
                      </line>
                      <circle cx="22" cy="-12" r="2" fill="#c6c6c8" opacity="0.7">
                        <animate attributeName="cy" values="-12;-10;-12" dur="1.5s" repeatCount="indefinite"/>
                      </circle>
                      <circle cx="25" cy="2" r="2" fill="#c6c6c8" opacity="0.5">
                        <animate attributeName="cy" values="2;4;2" dur="2s" repeatCount="indefinite"/>
                      </circle>
                    </g>
                  </svg>
                )}
                {/* Gradient overlay */}
                <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(160deg, rgba(14,14,15,0.15) 0%, rgba(14,14,15,0.55) 100%)' }} />
                {/* Icon badge */}
                <div style={{ position: 'absolute', bottom: 14, left: 16, width: 36, height: 36, borderRadius: 8, background: 'rgba(14,14,15,0.7)', backdropFilter: 'blur(12px)', border: '1px solid rgba(198,198,200,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#c6c6c8', fontVariationSettings: "'FILL' 0, 'wght' 300" }}>{card.icon}</span>
                </div>
              </div>

              <div style={{ padding: '1.75rem 2rem 2rem' }}>
                {/* Label */}
                <p style={{ fontSize: '0.6rem', fontWeight: 300, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--outline-dim)', marginBottom: '1rem' }}>{card.label}</p>

                <h3 style={{ fontFamily: font, fontWeight: 300, fontSize: '1.1rem', color: 'var(--on-surface)', marginBottom: '0.5rem', letterSpacing: '0.02em' }}>{card.title}</h3>
                <p style={{ color: 'var(--outline)', fontSize: '0.85rem', lineHeight: 1.65, marginBottom: '1.75rem', fontWeight: 300 }}>{card.desc}</p>

                <span style={{ color: 'var(--on-muted)', fontSize: '0.75rem', fontWeight: 300, letterSpacing: '0.12em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {card.cta}
                  <span className="material-symbols-outlined" style={{ fontSize: 14 }}>arrow_forward</span>
                </span>
              </div>
            </GlowCard>
          ))}
        </div>

        <Footer />
      </main>
    </div>
  );
}
