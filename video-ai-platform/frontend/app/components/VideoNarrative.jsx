'use client';

import { useState, useEffect } from 'react';
import { GlowCard } from '@/components/ui/spotlight-card';
import { GlassButton } from '@/components/ui/liquid-glass-button';

const font = "'Manrope', sans-serif";

export default function VideoNarrative({ videoId }) {
  const [narrative, setNarrative] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showFull, setShowFull] = useState(false);

  useEffect(() => { fetchExistingNarrative(); }, [videoId]);

  const fetchExistingNarrative = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/videos/${videoId}/narrative`);
      if (response.ok) setNarrative(await response.json());
      else if (response.status === 404) setNarrative(null);
    } catch { /* no narrative yet */ }
  };

  const generateNarrative = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8000/api/videos/${videoId}/narrative`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to generate narrative');
      setNarrative(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: font }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--outline)', fontVariationSettings: "'FILL' 0, 'wght' 300" }}>auto_awesome</span>
          <h2 style={{ fontFamily: font, fontWeight: 300, fontSize: '1rem', color: 'var(--on-surface)', letterSpacing: '0.04em' }}>AI Narrative</h2>
        </div>
        {!loading && (
          <GlassButton onClick={generateNarrative} size="sm">
            <span className="material-symbols-outlined" style={{ fontSize: 13 }}>{narrative ? 'refresh' : 'auto_awesome'}</span>
            {narrative ? 'Regenerate' : 'Generate Narrative'}
          </GlassButton>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ padding: '3rem 2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite' }} />
          <p style={{ color: 'var(--outline)', fontFamily: font, fontWeight: 300, fontSize: '0.825rem', letterSpacing: '0.05em' }}>Generating narrative with Claude AI...</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div style={{ background: 'rgba(238,125,119,0.06)', border: '1px solid rgba(238,125,119,0.18)', borderRadius: 6, padding: '1rem 1.25rem', display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--error)', flexShrink: 0 }}>error_outline</span>
          <span style={{ color: 'var(--error)', fontFamily: font, fontWeight: 300, fontSize: '0.875rem' }}>{error}</span>
        </div>
      )}

      {/* Empty state */}
      {!narrative && !loading && !error && (
        <div style={{ padding: '3rem 2rem', textAlign: 'center' }}>
          <div style={{ width: 52, height: 52, borderRadius: '50%', background: 'rgba(198,198,200,0.04)', border: '1px solid rgba(198,198,200,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 24, color: 'var(--outline)', fontVariationSettings: "'FILL' 0, 'wght' 300" }}>menu_book</span>
          </div>
          <h3 style={{ fontFamily: font, fontWeight: 300, fontSize: '1rem', color: 'var(--on-muted)', marginBottom: '0.625rem', letterSpacing: '0.03em' }}>No narrative yet</h3>
          <p style={{ color: 'var(--outline)', fontSize: '0.875rem', maxWidth: 380, margin: '0 auto', fontFamily: font, lineHeight: 1.75, fontWeight: 300 }}>
            Generate an AI-powered narrative that describes everything happening in this video — scene by scene.
          </p>
        </div>
      )}

      {/* Narrative content */}
      {narrative && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

          {/* Full Narrative + Summary — side by side */}
          <div style={{ display: 'grid', gridTemplateColumns: narrative.summary ? '1fr 1fr' : '1fr', gap: '1.25rem', alignItems: 'start' }}>
            {/* Full Narrative */}
            <div style={{ padding: '1.75rem 2rem', background: 'rgba(198,198,200,0.02)', borderRadius: 8, border: '1px solid rgba(72,72,75,0.2)', height: '100%', display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
                <div style={{ width: 2, height: 16, background: 'linear-gradient(180deg, var(--primary), var(--outline))', borderRadius: 2, flexShrink: 0 }} />
                <span style={{ color: 'var(--outline)', fontSize: '0.62rem', fontWeight: 300, textTransform: 'uppercase', letterSpacing: '0.2em', fontFamily: font }}>Full Narrative</span>
              </div>
              <div style={{ position: 'relative', flex: 1 }}>
                <p style={{
                  color: 'var(--on-muted)', lineHeight: 1.9, fontSize: '0.9rem', fontFamily: font, fontWeight: 300,
                  ...(showFull ? {} : { display: '-webkit-box', WebkitLineClamp: 5, WebkitBoxOrient: 'vertical', overflow: 'hidden' }),
                }}>
                  {narrative.narrative}
                </p>
              </div>
              <button
                onClick={() => setShowFull(v => !v)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--outline)', fontSize: '0.68rem', fontWeight: 300, fontFamily: font, letterSpacing: '0.12em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.875rem 0 0', marginTop: 'auto', alignSelf: 'flex-start', transition: 'color 0.2s' }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--on-muted)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--outline)'}
              >
                {showFull ? 'See Less' : 'See More'}
                <span className="material-symbols-outlined" style={{ fontSize: 14, transition: 'transform 0.3s cubic-bezier(0.2,0,0,1)', transform: showFull ? 'rotate(180deg)' : 'rotate(0deg)', fontVariationSettings: "'FILL' 0, 'wght' 300" }}>expand_more</span>
              </button>
            </div>

            {/* Summary */}
            {narrative.summary && (
              <div style={{ padding: '1.75rem 2rem', background: 'rgba(198,198,200,0.02)', borderRadius: 8, border: '1px solid rgba(72,72,75,0.2)', height: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
                  <div style={{ width: 2, height: 16, background: 'linear-gradient(180deg, var(--primary), var(--outline))', borderRadius: 2, flexShrink: 0 }} />
                  <span style={{ color: 'var(--outline)', fontSize: '0.62rem', fontWeight: 300, textTransform: 'uppercase', letterSpacing: '0.2em', fontFamily: font }}>Summary</span>
                </div>
                <p style={{ color: 'var(--on-muted)', lineHeight: 1.9, fontSize: '0.9rem', fontFamily: font, fontWeight: 300 }}>{narrative.summary}</p>
              </div>
            )}
          </div>

          {/* Key Moments */}
          {narrative.key_moments && narrative.key_moments.length > 0 && (
            <div style={{ padding: '1.5rem 2rem', background: 'rgba(198,198,200,0.02)', borderRadius: 8, border: '1px solid rgba(72,72,75,0.2)' }}>
              <p style={{ color: 'var(--outline-dim)', fontSize: '0.62rem', fontWeight: 300, textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '1.25rem', fontFamily: font }}>Key Moments</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {narrative.key_moments.slice(0, 8).map((moment, i) => (
                  <div key={i} style={{ display: 'flex', gap: '1.25rem', padding: '1rem 1.25rem', background: 'rgba(198,198,200,0.02)', borderRadius: 6, borderLeft: '2px solid rgba(198,198,200,0.15)' }}>
                    <span style={{ color: 'var(--primary)', fontFamily: 'monospace', fontSize: '0.78rem', fontWeight: 400, minWidth: 44, flexShrink: 0 }}>{moment.timestamp}s</span>
                    <div style={{ flex: 1 }}>
                      <p style={{ color: 'var(--on-muted)', fontSize: '0.875rem', lineHeight: 1.6, marginBottom: moment.main_objects?.length ? '0.625rem' : 0, fontFamily: font, fontWeight: 300 }}>{moment.description}</p>
                      {moment.main_objects?.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                          {moment.main_objects.map((obj, idx) => (
                            <span key={idx} style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', color: 'var(--on-muted)', fontSize: '0.68rem', padding: '0.18rem 0.55rem', borderRadius: 3, fontFamily: font, fontWeight: 300 }}>{obj}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <span style={{ color: 'var(--outline-dim)', fontSize: '0.7rem', flexShrink: 0, fontFamily: font, fontWeight: 300 }}>{moment.object_count} det.</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata footer */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 0.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: 'var(--outline)', fontSize: '0.78rem', fontFamily: font, fontWeight: 300 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 12, color: 'var(--outline)' }}>ads_click</span>
                Confidence: <strong style={{ color: 'var(--on-muted)', marginLeft: 4, fontWeight: 300 }}>{narrative.confidence || 'medium'}</strong>
              </span>
              {narrative.metadata?.detection_count && (
                <span style={{ color: 'var(--outline)', fontSize: '0.78rem', fontFamily: font, fontWeight: 300 }}>{narrative.metadata.detection_count} detections analyzed</span>
              )}
              {narrative.metadata?.has_audio && (
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: 'var(--outline)', fontSize: '0.78rem', fontFamily: font, fontWeight: 300 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 12 }}>mic</span> Audio included
                </span>
              )}
            </div>
            {narrative.generated_at && (
              <span style={{ color: 'var(--outline-dim)', fontSize: '0.72rem', fontFamily: font, fontWeight: 300 }}>
                {new Date(typeof narrative.generated_at === 'number' ? narrative.generated_at * 1000 : narrative.generated_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
