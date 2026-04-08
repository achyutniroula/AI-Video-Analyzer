'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from 'aws-amplify/auth';
import { GlowCard } from '@/components/ui/spotlight-card';
import { GlassButton } from '@/components/ui/liquid-glass-button';

const font = "'Manrope', sans-serif";

const features = [
  {
    icon: 'visibility',
    title: 'Vision Models',
    desc: 'SigLIP scene embeddings · DepthAnything V2 depth & spatial layout · Mask2Former panoptic segmentation (things + stuff) · Scene Graph Generation for object-to-object spatial reasoning.',
  },
  {
    icon: 'directions_run',
    title: 'Motion & Tracking',
    desc: 'SlowFast action recognition with temporal modeling · ByteTrack multi-object tracking with persistent track IDs across frames.',
  },
  {
    icon: 'graphic_eq',
    title: 'Audio Intelligence',
    desc: 'Whisper speech transcription with audio embeddings · PANNs audio event classification and scene-level sound recognition.',
  },
  {
    icon: 'hub',
    title: 'Multi-Modal Fusion',
    desc: 'Cross-modal alignment of detections, depth maps, panoptic masks, scene embeddings, audio events, action labels, and spatial relationships into a unified scene representation.',
  },
  {
    icon: 'psychology',
    title: 'VLM Reasoning',
    desc: 'Qwen2-VL frame-level captioning and visual reasoning · Structured prompt engineering with context injection and token-length control.',
  },
  {
    icon: 'article',
    title: 'Narrative Generation',
    desc: 'Claude assembles timestamped narratives from scene segments, track-based groupings, action timelines, and audio summaries — with multi-frame coherence and high-level reasoning.',
  },
  {
    icon: 'play_circle',
    title: 'Interactive Playback',
    desc: 'Watch your video with live bounding box overlays, frame-by-frame detection chips, and per-frame confidence scores synced to playback.',
  },
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
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite' }} />
      </div>
    );
  }

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', fontFamily: font }}>

      {/* Background ambient glow */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-15%', right: '-10%', width: '55%', height: '55%', borderRadius: '50%', background: 'rgba(198,198,200,0.03)', filter: 'blur(120px)' }} />
        <div style={{ position: 'absolute', bottom: '-10%', left: '15%', width: '35%', height: '35%', borderRadius: '50%', background: 'rgba(37,38,40,0.06)', filter: 'blur(100px)' }} />
      </div>

      {/* Hero */}
      <div style={{ position: 'relative', zIndex: 1, minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 1.5rem' }}>

        {/* Wordmark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '5rem' }}>
          <div style={{ width: 32, height: 32, background: 'linear-gradient(135deg, var(--primary), var(--outline))', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 17, color: 'var(--bg)', fontVariationSettings: "'FILL' 1, 'wght' 500" }}>lens</span>
          </div>
          <div>
            <p style={{ fontSize: '1rem', fontWeight: 200, letterSpacing: '0.15em', color: 'var(--on-surface)' }}>VisionFlow</p>
            <p style={{ fontSize: '0.6rem', fontWeight: 300, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--outline)', marginTop: 2 }}>Video AI</p>
          </div>
        </div>

        {/* Headline */}
        <div style={{ textAlign: 'center', maxWidth: 820, marginBottom: '3rem' }}>
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(3rem, 8vw, 6rem)', lineHeight: 1.05, letterSpacing: '0.02em', color: 'var(--on-surface)', marginBottom: '2rem', filter: 'drop-shadow(0 0 15px var(--header-glow-1)) drop-shadow(0 0 30px var(--header-glow-2)) drop-shadow(0 0 45px var(--header-glow-3))' }}>
            Video Understanding<br />
            <span style={{ color: 'var(--outline)' }}>Redefined</span>
          </h1>
          <p style={{ color: 'var(--on-muted)', fontSize: 'clamp(0.9rem, 2vw, 1.05rem)', lineHeight: 1.8, fontWeight: 300, maxWidth: 600, margin: '0 auto' }}>
            A cloud‑native multimodal AI engine that analyzes video using advanced vision, audio, depth, and action‑recognition models — with scene understanding and Claude‑powered narrative generation.
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
          <p style={{ fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.25em', textTransform: 'uppercase', color: 'var(--outline)', marginBottom: '1.25rem' }}>Capabilities</p>
          <h2 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(1.75rem, 4vw, 2.5rem)', color: 'var(--on-surface)', letterSpacing: '0.03em', filter: 'drop-shadow(0 0 12px var(--header-glow-3)) drop-shadow(0 0 25px var(--header-glow-1))' }}>
            Powered by cutting-edge AI
          </h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
          {features.map((f, i) => (
            <GlowCard key={i} style={{ padding: '2.25rem 2.5rem', cursor: 'pointer', transition: 'all 0.3s cubic-bezier(0.2,0,0,1)', transform: 'scale(1)' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'scale(1.02)';
                e.currentTarget.style.boxShadow = '0 20px 80px rgba(0,0,0,0.25), 0 4px 24px rgba(0,0,0,0.15), inset 0 0 40px rgba(198, 119, 221, 0.12)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.boxShadow = '0 2px 16px rgba(0,0,0,0.08), inset 0 0 20px rgba(118, 184, 255, 0.03)';
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 22, color: 'var(--outline)', marginBottom: '1.25rem', display: 'block', fontVariationSettings: "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24" }}>{f.icon}</span>
              <h3 style={{ fontFamily: font, fontWeight: 300, fontSize: '1rem', color: 'var(--on-surface)', marginBottom: '0.625rem', letterSpacing: '0.02em' }}>{f.title}</h3>
              <p style={{ color: 'var(--on-muted)', fontSize: '0.875rem', lineHeight: 1.75, fontWeight: 300 }}>{f.desc}</p>
            </GlowCard>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div style={{ position: 'relative', zIndex: 1, padding: '1.5rem 3rem', borderTop: '1px solid rgba(72,72,75,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
        <p style={{ color: 'var(--outline-dim)', fontSize: '0.72rem', fontWeight: 300, letterSpacing: '0.12em', fontFamily: font }}>Developed by Achyut and Shoaib</p>
        <p style={{ color: 'var(--outline)', fontSize: '0.68rem', fontWeight: 300, letterSpacing: '0.1em', textTransform: 'uppercase', fontFamily: font }}>COSC 4896</p>
      </div>
    </div>
  );
}
