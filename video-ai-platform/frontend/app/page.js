'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from 'aws-amplify/auth';
import { GlowCard } from '@/components/ui/spotlight-card';
import { GlassButton } from '@/components/ui/liquid-glass-button';

const font = "'Manrope', sans-serif";

const features = [
  { icon: 'psychology', title: 'Multi-Model Detection', desc: 'YOLOv11, SAM2, CLIP, SigLIP, SlowFast and more — working in ensemble for maximum accuracy.' },
  { icon: 'bolt', title: 'Real-Time Analysis', desc: 'Frame-by-frame breakdown with bounding boxes, depth maps, panoptic segmentation and action recognition.' },
  { icon: 'article', title: 'AI Narratives', desc: 'Claude generates rich, human-readable descriptions of everything happening in your video.' },
  { icon: 'visibility', title: 'Scene Understanding', desc: 'Spatial relationships, scene graphs, and environmental context extracted automatically.' },
  { icon: 'graphic_eq', title: 'Audio Intelligence', desc: 'Whisper transcription, PANNs audio events, and audio-visual fusion analysis.' },
  { icon: 'play_circle', title: 'Interactive Playback', desc: 'Watch your video with live detection overlays and per-frame confidence scores.' },
];

export default function Home() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    getCurrentUser()
      .then(() => router.push('/dashboard'))
      .catch(() => setChecking(false));
  }, [router]);

  if (checking) {
    return (
      <div style={{ minHeight: '100vh', background: '#0e0e0f', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite' }} />
      </div>
    );
  }

  return (
    <div style={{ background: '#0e0e0f', minHeight: '100vh', fontFamily: font }}>

      {/* Background ambient glow */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-15%', right: '-10%', width: '55%', height: '55%', borderRadius: '50%', background: 'rgba(198,198,200,0.03)', filter: 'blur(120px)' }} />
        <div style={{ position: 'absolute', bottom: '-10%', left: '15%', width: '35%', height: '35%', borderRadius: '50%', background: 'rgba(37,38,40,0.06)', filter: 'blur(100px)' }} />
      </div>

      {/* Hero */}
      <div style={{ position: 'relative', zIndex: 1, minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 1.5rem' }}>

        {/* Wordmark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '5rem' }}>
          <div style={{ width: 28, height: 28, background: 'linear-gradient(135deg, #c6c6c8, #454749)', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#0e0e0f', fontVariationSettings: "'FILL' 1, 'wght' 400" }}>camera</span>
          </div>
          <span style={{ fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.2em', textTransform: 'uppercase', color: '#767578' }}>Video Understanding Platform</span>
        </div>

        {/* Headline */}
        <div style={{ textAlign: 'center', maxWidth: 820, marginBottom: '3rem' }}>
          <p style={{ fontSize: '0.7rem', fontWeight: 300, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#767578', marginBottom: '2rem' }}>
            AI-Powered Video Intelligence
          </p>
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(3rem, 8vw, 6rem)', lineHeight: 1.05, letterSpacing: '0.02em', color: '#e7e5e8', marginBottom: '2rem' }}>
            Video Understanding<br />
            <span style={{ color: '#767578' }}>Redefined</span>
          </h1>
          <p style={{ color: '#acaaae', fontSize: 'clamp(0.9rem, 2vw, 1.05rem)', lineHeight: 1.8, fontWeight: 300, maxWidth: 540, margin: '0 auto' }}>
            Analyze videos with 14 AI models simultaneously. Real-time object detection, scene understanding, and Claude-powered narratives.
          </p>
        </div>

        {/* CTAs */}
        <div style={{ display: 'flex', gap: '0.875rem', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' }}>
          <GlassButton size="lg" variant="primary" onClick={() => router.push('/signup')}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_forward</span>
            Get Started
          </GlassButton>
          <GlassButton size="lg" variant="secondary" onClick={() => router.push('/login')}>
            Sign In
          </GlassButton>
        </div>
      </div>

      {/* Features */}
      <div style={{ position: 'relative', zIndex: 1, padding: '6rem 1.5rem 8rem', maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
          <p style={{ fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#767578', marginBottom: '1.25rem' }}>Capabilities</p>
          <h2 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(1.75rem, 4vw, 2.5rem)', color: '#e7e5e8', letterSpacing: '0.03em' }}>
            Powered by cutting-edge AI
          </h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
          {features.map((f, i) => (
            <GlowCard key={i} style={{ padding: '2.25rem 2.5rem' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 22, color: '#767578', marginBottom: '1.25rem', display: 'block', fontVariationSettings: "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24" }}>{f.icon}</span>
              <h3 style={{ fontFamily: font, fontWeight: 300, fontSize: '1rem', color: '#e7e5e8', marginBottom: '0.625rem', letterSpacing: '0.02em' }}>{f.title}</h3>
              <p style={{ color: '#767578', fontSize: '0.875rem', lineHeight: 1.75, fontWeight: 300 }}>{f.desc}</p>
            </GlowCard>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div style={{ position: 'relative', zIndex: 1, padding: '1.5rem 3rem', borderTop: '1px solid rgba(72,72,75,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
        <p style={{ color: '#48484b', fontSize: '0.72rem', fontWeight: 300, letterSpacing: '0.12em', fontFamily: font }}>Developed by Achyut and Shoaib</p>
        <p style={{ color: '#2b2c2f', fontSize: '0.68rem', fontWeight: 300, letterSpacing: '0.1em', textTransform: 'uppercase', fontFamily: font }}>COSC 4896</p>
      </div>
    </div>
  );
}
