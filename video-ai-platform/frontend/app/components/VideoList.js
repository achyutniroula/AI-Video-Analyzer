'use client';

import { useState, useEffect } from 'react';
import { listVideos } from '../lib/api';
import Link from 'next/link';
import { GlowCard } from '@/components/ui/spotlight-card';
import { GlassButton } from '@/components/ui/liquid-glass-button';

const font = "'Manrope', sans-serif";

function StatusBadge({ status }) {
  const config = {
    completed: { color: '#6ee7b7', bg: 'rgba(52,211,153,0.06)', border: 'rgba(52,211,153,0.18)', icon: 'check_circle' },
    processing: { color: '#acaaae', bg: 'rgba(172,170,174,0.06)', border: 'rgba(172,170,174,0.18)', icon: 'progress_activity' },
    failed: { color: '#ee7d77', bg: 'rgba(238,125,119,0.06)', border: 'rgba(238,125,119,0.18)', icon: 'error' },
  };
  const c = config[status] || { color: '#767578', bg: 'rgba(118,117,120,0.06)', border: 'rgba(118,117,120,0.18)', icon: 'schedule' };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', background: c.bg, border: `1px solid ${c.border}`, color: c.color, fontSize: '0.68rem', fontWeight: 300, padding: '0.2rem 0.625rem', borderRadius: 3, textTransform: 'capitalize', letterSpacing: '0.08em', fontFamily: font }}>
      <span className="material-symbols-outlined" style={{ fontSize: 11, fontVariationSettings: "'FILL' 0, 'wght' 300" }}>{c.icon}</span>
      {status}
    </span>
  );
}

export default function VideoList() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => { loadVideos(); }, []);

  async function loadVideos() {
    try {
      setLoading(true);
      setError(null);
      const data = await listVideos();
      setVideos(data.videos);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const filteredVideos = videos.filter(v => filter === 'all' || v.status === filter);

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  if (loading) {
    return (
      <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite', margin: '0 auto 1rem' }} />
          <p style={{ color: '#767578', fontFamily: font, fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.05em' }}>Loading library...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ maxWidth: 560, margin: '4rem auto', padding: '0 1.5rem' }}>
        <GlowCard className="p-7">
          <p style={{ color: '#ee7d77', marginBottom: '1.25rem', fontFamily: font, fontSize: '0.875rem', fontWeight: 300 }}>Error loading videos: {error}</p>
          <GlassButton onClick={loadVideos} variant="secondary" size="sm">Try again</GlassButton>
        </GlowCard>
      </div>
    );
  }

  const filters = ['all', 'completed', 'processing', 'failed'];

  return (
    <div style={{ padding: '3.5rem 3rem', fontFamily: font }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '3rem', flexWrap: 'wrap', gap: '1.25rem' }}>
        <div>
          <p style={{ fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#767578', marginBottom: '1rem' }}>Library</p>
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(2rem, 4vw, 3rem)', color: '#e7e5e8', letterSpacing: '0.03em' }}>Recent Captures</h1>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <GlassButton onClick={loadVideos} variant="secondary" size="sm">
            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>refresh</span>
            Refresh
          </GlassButton>
          <Link href="/upload">
            <GlassButton size="sm">
              <span className="material-symbols-outlined" style={{ fontSize: 14 }}>upload</span>
              Import Media
            </GlassButton>
          </Link>
        </div>
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: '0.375rem', marginBottom: '2.5rem', flexWrap: 'wrap' }}>
        {filters.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '0.4rem 1rem',
            borderRadius: 3,
            fontSize: '0.72rem',
            fontWeight: 300,
            cursor: 'pointer',
            transition: 'all 0.2s cubic-bezier(0.2,0,0,1)',
            fontFamily: font,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            background: filter === f ? 'rgba(198,198,200,0.08)' : 'transparent',
            border: filter === f ? '1px solid rgba(198,198,200,0.2)' : '1px solid rgba(72,72,75,0.25)',
            color: filter === f ? '#b8b9bb' : '#767578',
          }}>
            {f} ({videos.filter(v => f === 'all' || v.status === f).length})
          </button>
        ))}
      </div>

      {/* Empty state */}
      {filteredVideos.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '6rem 0' }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, color: '#252628', display: 'block', marginBottom: '1.75rem', fontVariationSettings: "'FILL' 0, 'wght' 200, 'GRAD' 0, 'opsz' 48" }}>video_library</span>
          <h3 style={{ fontFamily: font, color: '#acaaae', fontWeight: 300, fontSize: '1.1rem', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>No captures</h3>
          <p style={{ color: '#767578', marginBottom: '2.5rem', fontFamily: font, fontSize: '0.875rem', fontWeight: 300 }}>
            {filter === 'all' ? 'Import a video to get started.' : `No ${filter} videos found.`}
          </p>
          <Link href="/upload"><GlassButton>Import Media</GlassButton></Link>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.25rem' }}>
          {filteredVideos.map(video => (
            <Link key={video.video_id} href={`/videos/${video.video_id}`} style={{ display: 'block', textDecoration: 'none' }}>
              <GlowCard
                style={{ cursor: 'pointer', transition: 'transform 0.3s cubic-bezier(0.2,0,0,1)' }}
                onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-3px) scale(1.005)'}
                onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0) scale(1)'}
              >
                {/* Thumbnail */}
                <div style={{ background: '#131315', aspectRatio: '16/9', display: 'flex', alignItems: 'center', justifyContent: 'center', borderBottom: '1px solid rgba(72,72,75,0.15)', position: 'relative', overflow: 'hidden' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 36, color: '#252628', fontVariationSettings: "'FILL' 0, 'wght' 200, 'GRAD' 0, 'opsz' 48" }}>movie</span>
                  <div style={{ position: 'absolute', top: '0.625rem', right: '0.625rem' }}>
                    <StatusBadge status={video.status} />
                  </div>
                </div>

                {/* Info */}
                <div style={{ padding: '1.25rem' }}>
                  <p style={{ color: '#e7e5e8', fontWeight: 300, fontSize: '0.825rem', fontFamily: font, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '1rem', letterSpacing: '0.02em' }}>
                    {video.video_id}
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
                    {video.metadata?.duration && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#48484b' }}>schedule</span>
                        <span style={{ color: '#767578', fontSize: '0.75rem', fontFamily: font, fontWeight: 300 }}>{video.metadata.duration?.toFixed(1)}s</span>
                      </div>
                    )}
                    {video.metadata?.width && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#48484b' }}>aspect_ratio</span>
                        <span style={{ color: '#767578', fontSize: '0.75rem', fontFamily: font, fontWeight: 300 }}>{video.metadata.width}×{video.metadata.height}</span>
                      </div>
                    )}
                    {video.metadata?.fps && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#48484b' }}>speed</span>
                        <span style={{ color: '#767578', fontSize: '0.75rem', fontFamily: font, fontWeight: 300 }}>{video.metadata.fps?.toFixed(0)} fps</span>
                      </div>
                    )}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#48484b' }}>calendar_today</span>
                      <span style={{ color: '#767578', fontSize: '0.75rem', fontFamily: font, fontWeight: 300 }}>{formatDate(video.created_at)}</span>
                    </div>
                  </div>

                  {video.status === 'completed' && video.total_detections !== undefined && (
                    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(72,72,75,0.15)', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                      <span style={{ color: '#b8b9bb', fontWeight: 300, fontSize: '0.95rem', fontFamily: font }}>{video.total_detections}</span>
                      <span style={{ color: '#48484b', fontSize: '0.77rem', fontFamily: font, fontWeight: 300, letterSpacing: '0.05em' }}>detection{video.total_detections !== 1 ? 's' : ''}</span>
                    </div>
                  )}

                  {video.status === 'failed' && video.error_message && (
                    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(72,72,75,0.15)' }}>
                      <p style={{ color: '#ee7d77', fontSize: '0.77rem', fontFamily: font, fontWeight: 300 }}>{video.error_message}</p>
                    </div>
                  )}
                </div>
              </GlowCard>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
