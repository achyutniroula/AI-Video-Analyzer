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

function PerceptionLayer({ video, detections }) {
  const frames = video.metadata?.frames_processed || video.frame_count;
  const tracked = video.summary?.unique_tracked_objects;
  const sceneCount = video.scenes?.length || video.scene_types?.length;
  const compositionKeys = video.scene_composition ? Object.keys(video.scene_composition).length : 0;

  const models = [
    {
      name: 'SigLIP',
      role: 'Semantic classification',
      detail: sceneCount ? `${sceneCount} scene type${sceneCount !== 1 ? 's' : ''} identified` : 'Visual embeddings encoded',
      icon: 'image_search',
    },
    {
      name: 'DepthAnything V2',
      role: 'Monocular depth estimation',
      detail: frames ? `Depth maps for ${frames} frames` : 'Depth maps generated',
      icon: 'landscape',
    },
    {
      name: 'Mask2Former',
      role: 'Panoptic segmentation',
      detail: detections.length > 0 ? `${detections.length} detections segmented` : 'Scene masks computed',
      icon: 'shape_line',
    },
    {
      name: 'SceneGraph',
      role: 'Spatial relationship modeling',
      detail: compositionKeys > 0 ? `${compositionKeys} composition features mapped` : 'Object relationships modeled',
      icon: 'hub',
    },
    {
      name: 'SlowFast R50',
      role: 'Action recognition',
      detail: frames ? `Motion dynamics across ${frames} frames` : 'Temporal patterns analyzed',
      icon: 'play_circle',
    },
    {
      name: 'ByteTrack',
      role: 'Multi-object tracking',
      detail: tracked != null ? `${tracked} unique object${tracked !== 1 ? 's' : ''} tracked` : 'Object trajectories computed',
      icon: 'track_changes',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
      {models.map((m, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.875rem', padding: '0.875rem 1rem', background: 'rgba(198,198,200,0.02)', border: '1px solid rgba(72,72,75,0.12)', borderRadius: 6 }}>
          <div style={{ width: 30, height: 30, borderRadius: 6, background: 'rgba(72,72,75,0.12)', border: '1px solid rgba(72,72,75,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 15, color: 'var(--outline)', fontVariationSettings: "'FILL' 0, 'wght' 300" }}>{m.icon}</span>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.2rem' }}>
              <span style={{ color: 'var(--on-muted)', fontSize: '0.8rem', fontWeight: 300, fontFamily: font }}>{m.name}</span>
              <span style={{ color: 'var(--outline-dim)', fontSize: '0.62rem', fontWeight: 300, fontFamily: font, textTransform: 'uppercase', letterSpacing: '0.12em' }}>{m.role}</span>
            </div>
            <span style={{ color: 'var(--outline)', fontSize: '0.75rem', fontWeight: 300, fontFamily: font }}>{m.detail}</span>
          </div>
        </div>
      ))}
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
  const [audioAnalysis, setAudioAnalysis] = useState(undefined); // undefined = not yet fetched; null = fetched but empty
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
          // Set audio analysis — even null so the section always renders
          setAudioAnalysis(detectionsData.audio_analysis ?? null);
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.375rem' }}>
            <h1 style={{ fontFamily: font, fontWeight: 300, fontSize: '1.25rem', color: 'var(--on-surface)', letterSpacing: '0.02em', filter: 'drop-shadow(0 0 10px var(--header-glow-3)) drop-shadow(0 0 20px var(--header-glow-1))' }}>
              {video.display_name || videoId}
            </h1>
            <StatusBadge status={video.status} />
          </div>
          {video.display_name && video.display_name !== videoId && (
            <p style={{ color: 'var(--outline-dim)', fontSize: '0.72rem', fontFamily: 'monospace', letterSpacing: '0.04em', marginBottom: '0.25rem' }}>{videoId}</p>
          )}
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

        {/* Video player */}
        <div style={{ marginBottom: '1.5rem' }}>

          {/* Video Player */}
          <GlowCard style={{ overflow: 'hidden' }}>
            <div style={{ padding: '1.125rem 1.375rem', borderBottom: '1px solid rgba(72,72,75,0.15)' }}>
              <SectionLabel>Playback</SectionLabel>
            </div>
            <div style={{ padding: '1.375rem' }}>
              <VideoPlayer video={{ ...video, detections }} />
            </div>
          </GlowCard>

        </div>

        {/* AI Narrative — full width */}
        <GlowCard style={{ marginBottom: '1.5rem', padding: '2rem 2.25rem' }}>
          <SectionLabel>AI Narrative</SectionLabel>
          <VideoNarrative videoId={videoId} />
        </GlowCard>

        {/* Audio Narrative — always rendered once detections have loaded */}
        {audioAnalysis !== undefined && (
          <GlowCard style={{ marginBottom: '1.5rem', padding: '2rem 2.25rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--outline)', fontVariationSettings: "'FILL' 0, 'wght' 300" }}>graphic_eq</span>
                <h2 style={{ fontFamily: font, fontWeight: 300, fontSize: '1rem', color: 'var(--on-surface)', letterSpacing: '0.04em' }}>Audio Narrative</h2>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {[
                  { label: 'Whisper large-v3', icon: 'mic', desc: 'OpenAI Whisper large-v3 — high-accuracy speech recognition' },
                  { label: 'HTS-AT', icon: 'surround_sound', desc: 'Hierarchical Token-Semantic Audio Transformer — environmental sound classification' },
                  { label: 'Chromaprint', icon: 'music_note', desc: 'Chromaprint + AcoustID — acoustic fingerprinting for music identification' },
                ].map(src => (
                  <span key={src.label} title={src.desc} style={{
                    display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                    background: 'rgba(198,198,200,0.04)', border: '1px solid rgba(72,72,75,0.2)',
                    color: 'var(--outline)', fontSize: '0.65rem', fontWeight: 300,
                    padding: '0.2rem 0.65rem', borderRadius: 3, fontFamily: font, letterSpacing: '0.06em',
                  }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 11, fontVariationSettings: "'FILL' 0, 'wght' 300" }}>{src.icon}</span>
                    {src.label}
                  </span>
                ))}
              </div>
            </div>

            {/* No audio data (video processed before audio logging was enabled) */}
            {!audioAnalysis ? (
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.875rem', padding: '1.25rem 1.5rem', background: 'rgba(198,198,200,0.02)', border: '1px solid rgba(72,72,75,0.15)', borderRadius: 6 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--outline-dim)', flexShrink: 0, marginTop: 2, fontVariationSettings: "'FILL' 0, 'wght' 300" }}>info</span>
                <div>
                  <p style={{ color: 'var(--on-muted)', fontSize: '0.85rem', fontWeight: 300, fontFamily: font, marginBottom: '0.375rem' }}>
                    Audio data not available for this video.
                  </p>
                  <p style={{ color: 'var(--outline-dim)', fontSize: '0.78rem', fontWeight: 300, fontFamily: font, lineHeight: 1.7 }}>
                    This video was processed before the audio pipeline was added. Re-upload or process a new video to see Whisper large-v3 transcription, HTS-AT sound events, and music identification.
                  </p>
                </div>
              </div>
            ) : (
              /* Has audio data — two-column layout */
              <div style={{ display: 'grid', gridTemplateColumns: audioAnalysis.transcription ? '1fr 1fr' : '1fr', gap: '1.5rem', alignItems: 'start' }}>

                {/* Whisper transcription */}
                {audioAnalysis.transcription ? (
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                      <div style={{ width: 2, height: 14, background: 'linear-gradient(180deg, var(--primary), var(--outline))', borderRadius: 2, flexShrink: 0 }} />
                      <span style={{ color: 'var(--outline)', fontSize: '0.62rem', fontWeight: 300, textTransform: 'uppercase', letterSpacing: '0.2em', fontFamily: font }}>Whisper large-v3 — Speech Transcript</span>
                    </div>
                    <div style={{ background: 'rgba(198,198,200,0.02)', border: '1px solid rgba(72,72,75,0.18)', borderRadius: 6, padding: '1.25rem 1.5rem' }}>
                      <p style={{ color: 'var(--on-muted)', fontSize: '0.875rem', fontWeight: 300, lineHeight: 1.9, fontFamily: font, margin: 0, fontStyle: 'italic' }}>
                        "{audioAnalysis.transcription}"
                      </p>
                    </div>
                    <p style={{ color: 'var(--outline-dim)', fontSize: '0.68rem', fontWeight: 300, fontFamily: font, marginTop: '0.625rem' }}>
                      Whisper large-v3 — high-accuracy speech recognition
                      {audioAnalysis.speech_confidence > 0 && (
                        <span style={{ marginLeft: '0.5rem', color: 'var(--outline-dim)' }}>· {(audioAnalysis.speech_confidence * 100).toFixed(0)}% confidence</span>
                      )}
                    </p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', padding: '1.25rem 1.5rem', background: 'rgba(198,198,200,0.02)', border: '1px solid rgba(72,72,75,0.15)', borderRadius: 6 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--outline-dim)', fontVariationSettings: "'FILL' 0, 'wght' 300" }}>voice_over_off</span>
                    <span style={{ color: 'var(--outline)', fontSize: '0.825rem', fontWeight: 300, fontFamily: font }}>No speech detected by Whisper</span>
                  </div>
                )}

                {/* HTS-AT sound events + music identification */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

                  {/* HTS-AT events */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                      <div style={{ width: 2, height: 14, background: 'linear-gradient(180deg, var(--primary), var(--outline))', borderRadius: 2, flexShrink: 0 }} />
                      <span style={{ color: 'var(--outline)', fontSize: '0.62rem', fontWeight: 300, textTransform: 'uppercase', letterSpacing: '0.2em', fontFamily: font }}>HTS-AT — Detected Events</span>
                    </div>

                    {/* Badges: speech + dominant type */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
                        background: audioAnalysis.has_speech ? 'rgba(110,231,183,0.06)' : 'rgba(72,72,75,0.08)',
                        border: `1px solid ${audioAnalysis.has_speech ? 'rgba(110,231,183,0.2)' : 'rgba(72,72,75,0.18)'}`,
                        color: audioAnalysis.has_speech ? '#6ee7b7' : 'var(--outline)',
                        fontSize: '0.72rem', fontWeight: 300, padding: '0.2rem 0.625rem', borderRadius: 3, fontFamily: font,
                      }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 11 }}>{audioAnalysis.has_speech ? 'record_voice_over' : 'voice_over_off'}</span>
                        {audioAnalysis.has_speech ? 'Speech detected' : 'No speech'}
                      </span>
                      {audioAnalysis.dominant_type && (
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
                          background: 'rgba(198,198,200,0.04)', border: '1px solid rgba(72,72,75,0.18)',
                          color: 'var(--outline)', fontSize: '0.72rem', fontWeight: 300,
                          padding: '0.2rem 0.625rem', borderRadius: 3, fontFamily: font, textTransform: 'capitalize',
                        }}>
                          <span className="material-symbols-outlined" style={{ fontSize: 11, fontVariationSettings: "'FILL' 0, 'wght' 300" }}>equalizer</span>
                          {audioAnalysis.dominant_type}
                        </span>
                      )}
                    </div>

                    {audioAnalysis.audio_events?.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                        {audioAnalysis.audio_events.map((ev, i) => (
                          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
                            <span style={{ color: 'var(--on-muted)', fontSize: '0.825rem', fontWeight: 300, fontFamily: font, flex: 1, textTransform: 'capitalize' }}>{ev.event}</span>
                            {ev.confidence != null && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', flexShrink: 0 }}>
                                <div style={{ width: 80, height: 2, background: 'rgba(72,72,75,0.25)', borderRadius: 1 }}>
                                  <div style={{ width: `${(ev.confidence * 100).toFixed(0)}%`, height: '100%', background: i === 0 ? 'var(--primary)' : 'var(--outline)', borderRadius: 1, opacity: 1 - i * 0.12 }} />
                                </div>
                                <span style={{ color: 'var(--outline-dim)', fontSize: '0.68rem', fontFamily: font, minWidth: 32, textAlign: 'right' }}>{(ev.confidence * 100).toFixed(0)}%</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ color: 'var(--outline-dim)', fontSize: '0.825rem', fontWeight: 300, fontFamily: font }}>No sound events detected above threshold.</p>
                    )}
                    <p style={{ color: 'var(--outline-dim)', fontSize: '0.68rem', fontWeight: 300, fontFamily: font, marginTop: '0.875rem' }}>
                      HTS-AT via LAION CLAP — zero-shot classification across 28 sound categories
                    </p>
                    {audioAnalysis.fusion_notes && (
                      <p style={{ color: 'var(--outline-dim)', fontSize: '0.68rem', fontWeight: 300, fontFamily: font, marginTop: '0.375rem', fontStyle: 'italic' }}>
                        {audioAnalysis.fusion_notes}
                      </p>
                    )}
                  </div>

                  {/* Music identification */}
                  <div style={{ paddingTop: '1.125rem', borderTop: '1px solid rgba(72,72,75,0.12)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                      <div style={{ width: 2, height: 14, background: 'linear-gradient(180deg, var(--primary), var(--outline))', borderRadius: 2, flexShrink: 0 }} />
                      <span style={{ color: 'var(--outline)', fontSize: '0.62rem', fontWeight: 300, textTransform: 'uppercase', letterSpacing: '0.2em', fontFamily: font }}>Chromaprint — Music Identification</span>
                    </div>

                    {audioAnalysis.has_music && audioAnalysis.music_match ? (
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', padding: '1rem 1.25rem', background: 'rgba(110,231,183,0.03)', border: '1px solid rgba(110,231,183,0.12)', borderRadius: 6 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 20, color: '#6ee7b7', flexShrink: 0, marginTop: 2, fontVariationSettings: "'FILL' 0, 'wght' 300" }}>music_note</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ color: 'var(--on-surface)', fontSize: '0.9rem', fontWeight: 300, fontFamily: font, marginBottom: '0.25rem' }}>
                            {audioAnalysis.music_match.title}
                          </p>
                          <p style={{ color: 'var(--outline)', fontSize: '0.8rem', fontWeight: 300, fontFamily: font, marginBottom: '0.625rem' }}>
                            {audioAnalysis.music_match.artist}
                          </p>
                          <span style={{
                            display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
                            background: 'rgba(110,231,183,0.06)', border: '1px solid rgba(110,231,183,0.18)',
                            color: '#6ee7b7', fontSize: '0.68rem', fontWeight: 300, padding: '0.15rem 0.55rem', borderRadius: 3, fontFamily: font,
                          }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 10 }}>fingerprint</span>
                            {(audioAnalysis.music_match.confidence * 100).toFixed(0)}% match
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', padding: '0.875rem 1.25rem', background: 'rgba(198,198,200,0.02)', border: '1px solid rgba(72,72,75,0.12)', borderRadius: 6 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 15, color: 'var(--outline-dim)', fontVariationSettings: "'FILL' 0, 'wght' 300" }}>music_off</span>
                        <span style={{ color: 'var(--outline-dim)', fontSize: '0.8rem', fontWeight: 300, fontFamily: font }}>No music identified</span>
                      </div>
                    )}
                    <p style={{ color: 'var(--outline-dim)', fontSize: '0.68rem', fontWeight: 300, fontFamily: font, marginTop: '0.75rem' }}>
                      Chromaprint + AcoustID — acoustic fingerprinting matched against MusicBrainz
                    </p>
                  </div>

                </div>
              </div>
            )}
          </GlowCard>
        )}

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

        {/* Perception Layer */}
        <GlowCard style={{ marginBottom: '1.5rem', padding: '2rem 2.25rem' }}>
          <SectionLabel>Perception Layer</SectionLabel>
          <PerceptionLayer video={video} detections={detections} />
        </GlowCard>

        <Footer />
      </main>
    </div>
  );
}
