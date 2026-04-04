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
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(2.5rem, 5vw, 4rem)', lineHeight: 1.05, letterSpacing: '0.02em', color: 'var(--on-surface)', marginBottom: '0.75rem' }}>
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
              <div style={{ height: 148, overflow: 'hidden', borderRadius: '10px 10px 0 0', position: 'relative' }}>
                <img
                  src={[
                    'https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?w=700&q=80',
                    'https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?w=700&q=80',
                    'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=700&q=80',
                  ][i]}
                  alt={card.title}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
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
