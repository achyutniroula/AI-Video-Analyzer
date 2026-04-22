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
              <div style={{ height: 200, overflow: 'hidden', borderRadius: '10px 10px 0 0', position: 'relative', background: '#0e0e0f' }}>
                {i === 0 && (
                  <svg width="100%" height="100%" viewBox="0 0 400 200" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id="uploadBg" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#141416" />
                        <stop offset="100%" stopColor="#1e1e22" />
                      </linearGradient>
                      <linearGradient id="uploadAccent" x1="0%" y1="100%" x2="0%" y2="0%">
                        <stop offset="0%" stopColor="#c6c6c8" stopOpacity="0" />
                        <stop offset="100%" stopColor="#c6c6c8" stopOpacity="0.12" />
                      </linearGradient>
                    </defs>
                    <rect width="400" height="200" fill="url(#uploadBg)"/>
                    {/* dot grid */}
                    {[0,1,2,3,4,5,6,7,8,9].map(col => [0,1,2,3,4].map(row => (
                      <circle key={`${col}-${row}`} cx={col*44+22} cy={row*44+22} r="1.2" fill="#c6c6c8" opacity="0.07"/>
                    )))}
                    {/* rising particles */}
                    {[80,160,240,320].map((x, idx) => (
                      <circle key={idx} cx={x} cy="160" r="2.5" fill="#c6c6c8" opacity="0.25">
                        <animate attributeName="cy" values="170;30;170" dur={`${2.4+idx*0.5}s`} repeatCount="indefinite" begin={`${idx*0.6}s`}/>
                        <animate attributeName="opacity" values="0;0.35;0" dur={`${2.4+idx*0.5}s`} repeatCount="indefinite" begin={`${idx*0.6}s`}/>
                      </circle>
                    ))}
                    {/* drop zone box */}
                    <rect x="120" y="48" width="160" height="104" rx="10" fill="url(#uploadAccent)" stroke="#c6c6c8" strokeWidth="1" strokeDasharray="6,4" opacity="0.5"/>
                    {/* upload arrow */}
                    <g transform="translate(200,95)">
                      <line x1="0" y1="22" x2="0" y2="-10" stroke="#c6c6c8" strokeWidth="2.5" strokeLinecap="round">
                        <animateTransform attributeName="transform" type="translate" values="0,0;0,-8;0,0" dur="1.8s" repeatCount="indefinite"/>
                      </line>
                      <polyline points="-12,4 0,-12 12,4" fill="none" stroke="#c6c6c8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <animateTransform attributeName="transform" type="translate" values="0,0;0,-8;0,0" dur="1.8s" repeatCount="indefinite"/>
                      </polyline>
                    </g>
                    {/* progress bar */}
                    <rect x="140" y="132" width="120" height="3" rx="1.5" fill="#2a2a2e"/>
                    <rect x="140" y="132" width="120" height="3" rx="1.5" fill="#c6c6c8" opacity="0.5">
                      <animate attributeName="width" values="0;120;0" dur="2.8s" repeatCount="indefinite"/>
                    </rect>
                  </svg>
                )}
                {i === 1 && (
                  <svg width="100%" height="100%" viewBox="0 0 400 200" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id="videoBg" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#141416" />
                        <stop offset="100%" stopColor="#1e1e22" />
                      </linearGradient>
                    </defs>
                    <rect width="400" height="200" fill="url(#videoBg)"/>
                    {/* stacked thumbnail cards */}
                    <rect x="52" y="62" width="130" height="82" rx="6" fill="#252528" stroke="#c6c6c8" strokeWidth="0.5" opacity="0.35" transform="rotate(-4,117,103)"/>
                    <rect x="58" y="58" width="130" height="82" rx="6" fill="#2a2a2e" stroke="#c6c6c8" strokeWidth="0.5" opacity="0.6" transform="rotate(-1.5,123,99)"/>
                    {/* main screen */}
                    <rect x="66" y="52" width="130" height="82" rx="6" fill="#1c1c1f" stroke="#c6c6c8" strokeWidth="1" opacity="0.9"/>
                    {/* scanline pulse */}
                    <rect x="66" y="52" width="130" height="4" rx="2" fill="#c6c6c8" opacity="0.06">
                      <animate attributeName="y" values="52;130;52" dur="3s" repeatCount="indefinite"/>
                    </rect>
                    {/* play button */}
                    <circle cx="131" cy="93" r="20" fill="none" stroke="#c6c6c8" strokeWidth="1" opacity="0.4"/>
                    <polygon points="124,83 124,103 148,93" fill="#c6c6c8" opacity="0.75">
                      <animate attributeName="opacity" values="0.75;0.35;0.75" dur="2s" repeatCount="indefinite"/>
                    </polygon>
                    {/* film strip right side */}
                    <rect x="220" y="52" width="110" height="82" rx="4" fill="#1a1a1c" stroke="#c6c6c8" strokeWidth="0.5" opacity="0.5"/>
                    {[0,1,2,3].map(n => (
                      <rect key={n} x="228" y={60+n*19} width="94" height="14" rx="2" fill="#252528" stroke="#c6c6c8" strokeWidth="0.3" opacity="0.7">
                        <animate attributeName="opacity" values="0.7;0.4;0.7" dur={`${1.5+n*0.3}s`} repeatCount="indefinite" begin={`${n*0.2}s`}/>
                      </rect>
                    ))}
                    {/* bottom metadata bars */}
                    <rect x="66" y="148" width="80" height="3" rx="1.5" fill="#c6c6c8" opacity="0.2"/>
                    <rect x="66" y="155" width="55" height="3" rx="1.5" fill="#c6c6c8" opacity="0.12"/>
                    <rect x="220" y="148" width="60" height="3" rx="1.5" fill="#c6c6c8" opacity="0.2"/>
                    <rect x="220" y="155" width="40" height="3" rx="1.5" fill="#c6c6c8" opacity="0.12"/>
                  </svg>
                )}
                {i === 2 && (
                  <svg width="100%" height="100%" viewBox="0 0 400 200" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id="logsBg" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#141416" />
                        <stop offset="100%" stopColor="#161618" />
                      </linearGradient>
                    </defs>
                    <rect width="400" height="200" fill="url(#logsBg)"/>
                    {/* terminal window chrome */}
                    <rect x="30" y="28" width="340" height="148" rx="8" fill="#0e0e10" stroke="#2e2e32" strokeWidth="1"/>
                    {/* title bar */}
                    <rect x="30" y="28" width="340" height="26" rx="8" fill="#1a1a1c"/>
                    <rect x="30" y="44" width="340" height="10" fill="#1a1a1c"/>
                    <circle cx="52" cy="41" r="4.5" fill="#ff5f57" opacity="0.7"/>
                    <circle cx="68" cy="41" r="4.5" fill="#febc2e" opacity="0.7"/>
                    <circle cx="84" cy="41" r="4.5" fill="#28c840" opacity="0.7"/>
                    <rect x="140" y="37" width="120" height="8" rx="4" fill="#2a2a2e" opacity="0.6"/>
                    {/* log rows */}
                    {[
                      {y:72,  dotColor:'#28c840', w1:28, w2:90,  w3:60},
                      {y:90,  dotColor:'#28c840', w1:28, w2:110, w3:45},
                      {y:108, dotColor:'#febc2e', w1:28, w2:75,  w3:80},
                      {y:126, dotColor:'#28c840', w1:28, w2:100, w3:55},
                      {y:144, dotColor:'#28c840', w1:28, w2:85,  w3:70},
                    ].map((row, idx) => (
                      <g key={idx}>
                        <circle cx="50" cy={row.y+4} r="3.5" fill={row.dotColor} opacity="0.8"/>
                        <rect x="62" y={row.y} width={row.w1} height="6" rx="2" fill="#c6c6c8" opacity="0.18"/>
                        <rect x={62+row.w1+8} y={row.y} width={row.w2} height="6" rx="2" fill="#c6c6c8" opacity="0.28"/>
                        <rect x={62+row.w1+8+row.w2+8} y={row.y} width={row.w3} height="6" rx="2" fill="#c6c6c8" opacity="0.14"/>
                      </g>
                    ))}
                    {/* active / typing row */}
                    <circle cx="50" cy="166" r="3.5" fill="#c6c6c8" opacity="0.4"/>
                    <rect x="62" y="162" width="28" height="6" rx="2" fill="#c6c6c8" opacity="0.18"/>
                    <rect x="98" y="162" height="6" rx="2" fill="#c6c6c8" opacity="0.5">
                      <animate attributeName="width" values="0;120;0" dur="2.2s" repeatCount="indefinite"/>
                    </rect>
                    {/* blinking cursor */}
                    <rect x="98" y="162" width="6" height="6" rx="1" fill="#c6c6c8" opacity="0.8">
                      <animate attributeName="x" values="98;218;98" dur="2.2s" repeatCount="indefinite"/>
                      <animate attributeName="opacity" values="0.8;0.8;0" dur="0.6s" repeatCount="indefinite"/>
                    </rect>
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
