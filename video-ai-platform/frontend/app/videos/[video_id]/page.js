'use client';

import ModelBreakdown from '../../components/ModelBreakdown';
import VideoNarrative from '../../components/VideoNarrative';
import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
import { getVideoDetails } from '../../lib/api';
import Link from 'next/link';
import DetectionCharts from '../../components/DetectionCharts';
import VideoPlayer from '../../components/VideoPlayer';
import { GlowCard } from '@/components/ui/spotlight-card';
import Sidebar from '../../components/Sidebar';
import Footer from '../../components/Footer';

const font = "'Manrope', sans-serif";

function StatusBadge({ status }) {
  const config = {
    completed: { color: '#6ee7b7', bg: 'rgba(52,211,153,0.06)', border: 'rgba(52,211,153,0.18)', icon: 'check_circle' },
    processing: { color: '#acaaae', bg: 'rgba(172,170,174,0.06)', border: 'rgba(172,170,174,0.18)', icon: 'progress_activity' },
    failed: { color: '#ee7d77', bg: 'rgba(238,125,119,0.06)', border: 'rgba(238,125,119,0.18)', icon: 'error' },
  };
  const c = config[status] || { color: '#767578', bg: 'rgba(118,117,120,0.06)', border: 'rgba(118,117,120,0.18)', icon: 'schedule' };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', background: c.bg, border: `1px solid ${c.border}`, color: c.color, fontSize: '0.68rem', fontWeight: 300, padding: '0.2rem 0.75rem', borderRadius: 3, textTransform: 'capitalize', letterSpacing: '0.08em', fontFamily: font }}>
      <span className="material-symbols-outlined" style={{ fontSize: 11, fontVariationSettings: "'FILL' 0, 'wght' 300" }}>{c.icon}</span>
      {status}
    </span>
  );
}

function MetaItem({ icon, label, value }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: 'var(--outline-dim)' }}>
        <span className="material-symbols-outlined" style={{ fontSize: 12, fontVariationSettings: "'FILL' 0, 'wght' 300" }}>{icon}</span>
        <span style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.18em', fontWeight: 300, fontFamily: font }}>{label}</span>
      </div>
      <span style={{ color: 'var(--on-surface)', fontSize: '0.9rem', fontWeight: 300, fontFamily: font }}>{value ?? '—'}</span>
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <p style={{ fontSize: '0.62rem', fontWeight: 300, textTransform: 'uppercase', letterSpacing: '0.2em', color: 'var(--outline-dim)', marginBottom: '1.25rem', fontFamily: font }}>
      {children}
    </p>
  );
}

export default function VideoDetailPage() {
  const params = useParams();
  const router = useRouter();
  const videoId = params.video_id;

  const [video, setVideo] = useState(null);
  const [detections, setDetections] = useState([]);
  const [audioAnalysis, setAudioAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => { checkAuth(); }, []);

  async function checkAuth() {
    try {
      await getCurrentUser();
      loadVideoDetails();
    } catch {
      router.push('/login');
    }
  }

  function calculateSummary(detections) {
    if (!detections || detections.length === 0) return { total_detections: 0, by_class: {}, unique_tracked_objects: 0 };
    const by_class = {};
    detections.forEach(d => { by_class[d.class_name] = (by_class[d.class_name] || 0) + 1; });
    return { total_detections: detections.length, by_class, unique_tracked_objects: Object.keys(by_class).length };
  }

  async function loadVideoDetails() {
    try {
      setLoading(true);
      setError(null);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      if (!token) throw new Error('No authentication token');
      const data = await getVideoDetails(videoId);
      try {
        const detectionsRes = await fetch(`http://localhost:8000/api/videos/${videoId}/detections`, {
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        });
        if (detectionsRes.ok) {
          const detectionsData = await detectionsRes.json();
          if (detectionsData.audio_analysis) setAudioAnalysis(detectionsData.audio_analysis);
          setDetections(detectionsData.detections || []);
          if (!data.summary && detectionsData.detections?.length > 0) data.summary = calculateSummary(detectionsData.detections);
          if (!data.metadata && detectionsData.metadata) data.metadata = detectionsData.metadata;
          if (!data.metadata && (detectionsData.duration || detectionsData.frame_count)) {
            data.metadata = { duration: parseFloat(detectionsData.duration) || 0, frames_processed: detectionsData.frame_count || 0 };
          }
        } else {
          setDetections([]);
        }
      } catch { setDetections([]); }
      setVideo(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function getTopObjects(summary) {
    if (!summary?.by_class) return [];
    return Object.entries(summary.by_class).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([className, count]) => ({ className, count }));
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', fontFamily: font }}>
        <Sidebar />
        <main style={{ marginLeft: 256, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite' }} />
          <p style={{ color: '#767578', fontFamily: font, fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.05em' }}>Loading...</p>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', fontFamily: font }}>
        <Sidebar />
        <main style={{ marginLeft: 256, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem' }}>
          <GlowCard className="p-9" style={{ maxWidth: 480 }}>
            <h2 style={{ fontFamily: font, color: '#ee7d77', fontWeight: 300, fontSize: '1.1rem', marginBottom: '0.875rem', letterSpacing: '0.05em' }}>Error Loading Video</h2>
            <p style={{ color: '#ee7d77', marginBottom: '1.75rem', fontFamily: font, fontWeight: 300, fontSize: '0.875rem', opacity: 0.8 }}>{error}</p>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button onClick={loadVideoDetails} style={{ color: '#acaaae', background: 'none', border: '1px solid rgba(72,72,75,0.35)', borderRadius: 4, padding: '0.5rem 1.125rem', cursor: 'pointer', fontSize: '0.78rem', fontFamily: font, fontWeight: 300, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Try Again</button>
              <Link href="/videos" style={{ color: '#767578', fontSize: '0.78rem', display: 'flex', alignItems: 'center', fontFamily: font, fontWeight: 300, letterSpacing: '0.05em' }}>← Back to Videos</Link>
            </div>
          </GlowCard>
        </main>
      </div>
    );
  }

  if (!video) return null;

  const topObjects = getTopObjects(video.summary);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', fontFamily: font }}>
      <Sidebar />

      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-10%', right: '-5%', width: '45%', height: '45%', borderRadius: '50%', background: 'rgba(198,198,200,0.02)', filter: 'blur(120px)' }} />
      </div>

      <main style={{ marginLeft: 256, flex: 1, padding: '3.5rem 3rem 5rem', position: 'relative', zIndex: 1 }}>

        {/* Page label */}
        <p style={{ fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#767578', marginBottom: '1.25rem' }}>
          <Link href="/videos" style={{ color: '#48484b', transition: 'color 0.2s' }}
            onMouseEnter={e => e.currentTarget.style.color = '#767578'}
            onMouseLeave={e => e.currentTarget.style.color = '#48484b'}>
            Library
          </Link>
          {' / '}Capture Details
        </p>

        {/* Title + Status */}
        <div style={{ marginBottom: '2.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
            <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(1.4rem, 3vw, 2rem)', color: '#e7e5e8', letterSpacing: '0.02em', fontFamily: 'monospace', fontSize: '1.1rem', color: '#acaaae' }}>
              {videoId}
            </h1>
            <StatusBadge status={video.status} />
          </div>
          <p style={{ color: '#48484b', fontSize: '0.78rem', fontFamily: font, fontWeight: 300, letterSpacing: '0.05em' }}>Uploaded {formatDate(video.created_at)}</p>
        </div>

        {/* Metadata strip */}
        {video.metadata && (
          <GlowCard style={{ marginBottom: '1.5rem', padding: '1.75rem 2rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '1.75rem' }}>
              {video.metadata.width && <MetaItem icon="aspect_ratio" label="Resolution" value={`${video.metadata.width}×${video.metadata.height}`} />}
              {video.metadata.duration && <MetaItem icon="schedule" label="Duration" value={`${video.metadata.duration?.toFixed(1)}s`} />}
              {video.metadata.fps && <MetaItem icon="speed" label="FPS" value={video.metadata.fps?.toFixed(1)} />}
              {video.metadata.frames_processed && <MetaItem icon="movie" label="Frames" value={video.metadata.frames_processed} />}
              {video.summary?.total_detections !== undefined && <MetaItem icon="manage_search" label="Detections" value={video.summary.total_detections} />}
              {video.processed_at && <MetaItem icon="task_alt" label="Processed" value={formatDate(video.processed_at)} />}
            </div>
          </GlowCard>
        )}

        {/* Main two-column layout */}
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.5fr) minmax(0,1fr)', gap: '1.5rem', marginBottom: '1.5rem', alignItems: 'start' }}>

          {/* Video Player */}
          <GlowCard style={{ overflow: 'hidden' }}>
            <div style={{ padding: '1.125rem 1.375rem', borderBottom: '1px solid rgba(72,72,75,0.15)' }}>
              <SectionLabel>Playback</SectionLabel>
            </div>
            <div style={{ padding: '1.375rem' }}>
              <VideoPlayer video={{ ...video, detections }} />
            </div>
          </GlowCard>

          {/* Top Detections */}
          <GlowCard style={{ padding: '1.75rem 2rem' }}>
            <SectionLabel>Top Detections</SectionLabel>
            {topObjects.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {topObjects.map(({ className, count }, i) => {
                  const max = topObjects[0].count;
                  const pct = Math.round((count / max) * 100);
                  return (
                    <div key={i}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
                        <span style={{ color: 'var(--on-muted)', fontSize: '0.825rem', fontWeight: 300, textTransform: 'capitalize', fontFamily: font }}>{className}</span>
                        <span style={{ color: 'var(--outline)', fontSize: '0.825rem', fontWeight: 300, fontFamily: font }}>{count}</span>
                      </div>
                      <div style={{ height: 2, background: 'rgba(72,72,75,0.25)', borderRadius: 1 }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: `linear-gradient(90deg, #454749, #c6c6c8)`, borderRadius: 1, opacity: 1 - i * 0.15 }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p style={{ color: '#48484b', fontSize: '0.875rem', fontFamily: font, fontWeight: 300 }}>No detections yet.</p>
            )}

            {video.summary?.unique_tracked_objects !== undefined && (
              <div style={{ marginTop: '1.75rem', paddingTop: '1.375rem', borderTop: '1px solid rgba(72,72,75,0.15)' }}>
                <MetaItem icon="category" label="Unique Classes" value={video.summary.unique_tracked_objects} />
              </div>
            )}
          </GlowCard>
        </div>

        {/* AI Narrative */}
        <GlowCard style={{ marginBottom: '1.5rem', padding: '2rem 2.25rem' }}>
          <SectionLabel>AI Narrative</SectionLabel>
          <VideoNarrative videoId={videoId} />
        </GlowCard>

        {/* Detection Charts */}
        {detections.length > 0 && (
          <GlowCard style={{ marginBottom: '1.5rem', padding: '2rem 2.25rem' }}>
            <SectionLabel>Detection Charts</SectionLabel>
            <DetectionCharts video={video} />
          </GlowCard>
        )}

        {/* Model Breakdown */}
        {detections.length > 0 && (
          <GlowCard style={{ marginBottom: '1.5rem', padding: '2rem 2.25rem' }}>
            <SectionLabel>Model Breakdown</SectionLabel>
            <ModelBreakdown detections={detections} video={video} audio_analysis={audioAnalysis} />
          </GlowCard>
        )}

        {/* Detections Table */}
        {detections.length > 0 && (
          <GlowCard style={{ padding: '2rem 2.25rem' }}>
            <SectionLabel>
              Raw Detections <span style={{ color: '#252628', fontWeight: 300, textTransform: 'none', letterSpacing: 0, fontSize: '0.75rem' }}>({Math.min(detections.length, 100)} of {detections.length})</span>
            </SectionLabel>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(72,72,75,0.2)' }}>
                    {['Frame', 'Time', 'Class', 'Confidence', 'Model', 'Bounding Box'].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '0.625rem 1rem', color: '#48484b', fontWeight: 300, textTransform: 'uppercase', fontSize: '0.62rem', letterSpacing: '0.15em', fontFamily: font }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {detections.slice(0, 100).map((d, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid rgba(72,72,75,0.08)', transition: 'background 0.15s' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(198,198,200,0.02)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                      <td style={{ padding: '0.5rem 1rem', color: '#48484b', fontFamily: font, fontWeight: 300 }}>{d.frame_id}</td>
                      <td style={{ padding: '0.5rem 1rem', color: '#48484b', fontFamily: font, fontWeight: 300 }}>{d.timestamp?.toFixed(2)}s</td>
                      <td style={{ padding: '0.5rem 1rem', color: '#acaaae', fontWeight: 300, textTransform: 'capitalize', fontFamily: font }}>{d.class_name}</td>
                      <td style={{ padding: '0.5rem 1rem' }}>
                        <span style={{ color: d.confidence > 0.8 ? '#6ee7b7' : d.confidence > 0.6 ? '#b8b9bb' : '#ee7d77', fontWeight: 300, fontFamily: font }}>
                          {(d.confidence * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td style={{ padding: '0.5rem 1rem', color: '#48484b', fontFamily: 'monospace', fontSize: '0.72rem' }}>{d.model_source || '—'}</td>
                      <td style={{ padding: '0.5rem 1rem', color: '#48484b', fontFamily: 'monospace', fontSize: '0.72rem' }}>
                        {Array.isArray(d.bbox) ? `[${d.bbox.map(v => v?.toFixed(0)).join(', ')}]` : d.bbox ? JSON.stringify(d.bbox) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlowCard>
        )}

        <Footer />
      </main>
    </div>
  );
}
