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
  { icon: 'monitoring', label: 'System', title: 'System Status', desc: 'Monitor processing queue and worker health', href: '/videos', cta: 'View Status' },
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
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(2.5rem, 5vw, 4rem)', lineHeight: 1.05, letterSpacing: '0.02em', color: '#e7e5e8', marginBottom: '0.75rem' }}>
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
              <div style={{ height: 120, overflow: 'hidden', borderRadius: '10px 10px 0 0', position: 'relative', background: 'rgba(37,38,40,0.8)' }}>
                {i === 0 && (
                  /* Upload thumbnail — upward arrow motif */
                  <>
                    <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(135deg, rgba(72,72,75,0.25) 0%, rgba(37,38,40,0) 100%)' }} />
                    <div style={{ position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                      <div style={{ width: 2, height: 32, background: 'linear-gradient(180deg, rgba(198,198,200,0.6), rgba(198,198,200,0.1))' }} />
                      <div style={{ width: 0, height: 0, borderLeft: '6px solid transparent', borderRight: '6px solid transparent', borderBottom: '9px solid rgba(198,198,200,0.5)', position: 'absolute', top: -9, transform: 'translateY(-100%)' }} />
                    </div>
                    <div style={{ position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)', width: 44, height: 2, background: 'rgba(198,198,200,0.15)', borderRadius: 1 }} />
                    {[...Array(5)].map((_, j) => (
                      <div key={j} style={{ position: 'absolute', width: 2, height: 2, borderRadius: '50%', background: `rgba(198,198,200,${0.08 + j * 0.04})`, top: `${20 + j * 12}%`, left: `${15 + j * 16}%` }} />
                    ))}
                  </>
                )}
                {i === 1 && (
                  /* Library thumbnail — grid of video frame previews */
                  <div style={{ position: 'absolute', inset: 12, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gridTemplateRows: 'repeat(2, 1fr)', gap: 4 }}>
                    {[...Array(8)].map((_, j) => (
                      <div key={j} style={{ borderRadius: 3, background: `rgba(198,198,200,${0.04 + (j % 3) * 0.03})`, border: '1px solid rgba(72,72,75,0.25)', position: 'relative', overflow: 'hidden' }}>
                        <div style={{ position: 'absolute', top: '30%', left: '15%', right: '15%', height: 1, background: `rgba(198,198,200,${0.1 + (j % 2) * 0.08})`, borderRadius: 1 }} />
                        <div style={{ position: 'absolute', top: '60%', left: '15%', right: '30%', height: 1, background: `rgba(198,198,200,0.06)`, borderRadius: 1 }} />
                      </div>
                    ))}
                  </div>
                )}
                {i === 2 && (
                  /* System status thumbnail — pulse line graph */
                  <>
                    <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(135deg, rgba(37,38,40,0) 0%, rgba(72,72,75,0.15) 100%)' }} />
                    <svg viewBox="0 0 200 80" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', padding: '12px 16px' }} preserveAspectRatio="none">
                      <polyline points="0,55 25,50 50,35 75,40 100,20 125,30 150,25 175,35 200,28" fill="none" stroke="rgba(198,198,200,0.3)" strokeWidth="1.5" strokeLinejoin="round" />
                      <polyline points="0,65 25,62 50,58 75,60 100,52 125,55 150,50 175,53 200,48" fill="none" stroke="rgba(198,198,200,0.12)" strokeWidth="1" strokeLinejoin="round" />
                    </svg>
                    <div style={{ position: 'absolute', top: 14, right: 16, width: 6, height: 6, borderRadius: '50%', background: 'rgba(110,231,183,0.8)', boxShadow: '0 0 8px rgba(110,231,183,0.4)' }} />
                  </>
                )}
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
