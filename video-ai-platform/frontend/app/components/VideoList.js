'use client';

import { useState, useEffect } from 'react';
import { listVideos, deleteVideo, renameVideo, getThumbnailUrl } from '../lib/api';
import Link from 'next/link';
import { GlowCard } from '@/components/ui/spotlight-card';
import { GlassButton } from '@/components/ui/liquid-glass-button';

const font = "'Manrope', sans-serif";

function StatusBadge({ status, overlay = false }) {
  const config = {
    completed: { color: '#6ee7b7', bg: 'rgba(52,211,153,0.08)', border: 'rgba(110,231,183,0.35)', icon: 'check_circle' },
    processing: { color: '#d4d2d6', bg: 'rgba(172,170,174,0.08)', border: 'rgba(172,170,174,0.32)', icon: 'progress_activity' },
    failed:     { color: '#f0847e', bg: 'rgba(238,125,119,0.08)', border: 'rgba(238,125,119,0.35)', icon: 'error' },
  };
  const c = config[status] || { color: '#acaaae', bg: 'rgba(118,117,120,0.08)', border: 'rgba(118,117,120,0.3)', icon: 'schedule' };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
      background: overlay ? 'rgba(8,8,9,0.68)' : c.bg,
      backdropFilter: overlay ? 'blur(10px)' : 'none',
      WebkitBackdropFilter: overlay ? 'blur(10px)' : 'none',
      border: `1px solid ${c.border}`,
      color: c.color,
      fontSize: '0.68rem', fontWeight: 400,
      padding: '0.22rem 0.65rem', borderRadius: 4,
      textTransform: 'capitalize', letterSpacing: '0.08em', fontFamily: font,
      textShadow: overlay ? '0 1px 3px rgba(0,0,0,0.5)' : 'none',
    }}>
      <span className="material-symbols-outlined" style={{ fontSize: 11, fontVariationSettings: "'FILL' 0, 'wght' 400" }}>{c.icon}</span>
      {status}
    </span>
  );
}

function VideoCard({ video, onDelete, onRename }) {
  const [thumbnailUrl, setThumbnailUrl] = useState(null);
  const [renaming, setRenaming] = useState(false);
  const [draftName, setDraftName] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saving, setSaving] = useState(false);

  const displayName = video.display_name || video.video_id;

  useEffect(() => {
    getThumbnailUrl(video.video_id).then(url => { if (url) setThumbnailUrl(url); }).catch(() => {});
  }, [video.video_id]);

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteVideo(video.video_id);
      onDelete(video.video_id);
    } catch {
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  async function handleRename() {
    if (!draftName.trim() || draftName.trim() === displayName) { setRenaming(false); return; }
    setSaving(true);
    try {
      await renameVideo(video.video_id, draftName.trim());
      onRename(video.video_id, draftName.trim());
      setRenaming(false);
    } catch {}
    setSaving(false);
  }

  function startRename() {
    setDraftName(displayName);
    setRenaming(true);
  }

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  return (
    <GlowCard style={{ cursor: 'pointer', transition: 'transform 0.3s cubic-bezier(0.2,0,0,1)', position: 'relative' }}>
      {/* Thumbnail */}
      <Link href={`/videos/${video.video_id}`} style={{ display: 'block', textDecoration: 'none' }}>
        <div style={{ background: 'var(--surface-low)', aspectRatio: '16/9', position: 'relative', overflow: 'hidden', borderBottom: '1px solid var(--glass-border)' }}>
          {thumbnailUrl ? (
            <>
              <img src={thumbnailUrl} alt="thumbnail" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(160deg, transparent 50%, rgba(14,14,15,0.4) 100%)' }} />
            </>
          ) : (
            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 36, color: 'var(--outline-faint)', fontVariationSettings: "'FILL' 0, 'wght' 200" }}>movie</span>
            </div>
          )}
          <div style={{ position: 'absolute', top: '0.625rem', right: '0.625rem' }}>
            <StatusBadge status={video.status} overlay />
          </div>
        </div>
      </Link>

      {/* Info */}
      <div style={{ padding: '1.125rem 1.25rem 1.25rem' }}>
        {/* Name row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.875rem' }}>
          {renaming ? (
            <div style={{ display: 'flex', gap: '0.375rem', flex: 1 }}>
              <input
                autoFocus
                value={draftName}
                onChange={e => setDraftName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleRename(); if (e.key === 'Escape') setRenaming(false); }}
                style={{ flex: 1, background: 'var(--input-bg)', border: '1px solid var(--glass-border-h)', borderRadius: 4, padding: '0.3rem 0.625rem', color: 'var(--on-surface)', fontSize: '0.825rem', fontFamily: font, fontWeight: 300, outline: 'none' }}
              />
              <button onClick={handleRename} disabled={saving} style={{ background: 'rgba(110,231,183,0.1)', border: '1px solid rgba(110,231,183,0.25)', borderRadius: 3, cursor: 'pointer', padding: '0.3rem 0.5rem' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#6ee7b7' }}>check</span>
              </button>
              <button onClick={() => setRenaming(false)} style={{ background: 'transparent', border: '1px solid rgba(72,72,75,0.3)', borderRadius: 3, cursor: 'pointer', padding: '0.3rem 0.5rem' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--outline)' }}>close</span>
              </button>
            </div>
          ) : (
            <>
              <Link href={`/videos/${video.video_id}`} style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--on-surface)', fontWeight: 300, fontSize: '0.825rem', fontFamily: font, letterSpacing: '0.02em', textDecoration: 'none' }}>
                {displayName}
              </Link>
              <button onClick={startRename} title="Rename" style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.1rem', opacity: 0.5, transition: 'opacity 0.15s' }} onMouseEnter={e => e.currentTarget.style.opacity = '1'} onMouseLeave={e => e.currentTarget.style.opacity = '0.5'}>
                <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--outline)' }}>edit</span>
              </button>
            </>
          )}
        </div>

        {/* Meta */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginBottom: '1rem' }}>
          {video.metadata?.duration && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 12, color: 'var(--outline-dim)' }}>schedule</span>
              <span style={{ color: 'var(--outline)', fontSize: '0.75rem', fontFamily: font, fontWeight: 300 }}>{video.metadata.duration?.toFixed(1)}s</span>
            </div>
          )}
          {video.metadata?.width && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 12, color: 'var(--outline-dim)' }}>aspect_ratio</span>
              <span style={{ color: 'var(--outline)', fontSize: '0.75rem', fontFamily: font, fontWeight: 300 }}>{video.metadata.width}×{video.metadata.height}</span>
            </div>
          )}
          {video.metadata?.fps && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 12, color: 'var(--outline-dim)' }}>speed</span>
              <span style={{ color: 'var(--outline)', fontSize: '0.75rem', fontFamily: font, fontWeight: 300 }}>{video.metadata.fps?.toFixed(0)} fps</span>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 12, color: 'var(--outline-dim)' }}>calendar_today</span>
            <span style={{ color: 'var(--outline)', fontSize: '0.75rem', fontFamily: font, fontWeight: 300 }}>{formatDate(video.created_at)}</span>
          </div>
        </div>

        {video.status === 'completed' && video.total_detections !== undefined && (
          <div style={{ paddingTop: '0.875rem', borderTop: '1px solid var(--glass-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--on-muted)', fontWeight: 300, fontSize: '0.875rem', fontFamily: font }}>{video.total_detections} <span style={{ color: 'var(--outline)', fontSize: '0.77rem' }}>detection{video.total_detections !== 1 ? 's' : ''}</span></span>
            {/* Delete */}
            {confirmDelete ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                <span style={{ color: 'var(--outline)', fontSize: '0.72rem', fontFamily: font }}>Delete?</span>
                <button onClick={handleDelete} disabled={deleting} style={{ background: 'rgba(238,125,119,0.12)', border: '1px solid rgba(238,125,119,0.25)', borderRadius: 3, cursor: 'pointer', padding: '0.25rem 0.5rem' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#ee7d77' }}>check</span>
                </button>
                <button onClick={() => setConfirmDelete(false)} style={{ background: 'transparent', border: '1px solid var(--glass-border)', borderRadius: 3, cursor: 'pointer', padding: '0.25rem 0.5rem' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 13, color: 'var(--outline)' }}>close</span>
                </button>
              </div>
            ) : (
              <button onClick={() => setConfirmDelete(true)} title="Delete" style={{ background: 'none', border: 'none', cursor: 'pointer', opacity: 0.45, transition: 'opacity 0.15s' }} onMouseEnter={e => e.currentTarget.style.opacity = '1'} onMouseLeave={e => e.currentTarget.style.opacity = '0.45'}>
                <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#ee7d77' }}>delete</span>
              </button>
            )}
          </div>
        )}

        {video.status === 'failed' && video.error_message && (
          <div style={{ marginTop: '0.875rem', paddingTop: '0.875rem', borderTop: '1px solid var(--glass-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <p style={{ color: '#ee7d77', fontSize: '0.77rem', fontFamily: font, fontWeight: 300 }}>{video.error_message}</p>
            <button onClick={() => setConfirmDelete(true)} title="Delete" style={{ background: 'none', border: 'none', cursor: 'pointer', opacity: 0.5, transition: 'opacity 0.15s' }} onMouseEnter={e => e.currentTarget.style.opacity = '1'} onMouseLeave={e => e.currentTarget.style.opacity = '0.5'}>
              <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#ee7d77' }}>delete</span>
            </button>
          </div>
        )}

        {/* Delete confirm for non-completed/failed */}
        {!video.status?.match(/completed|failed/) && confirmDelete && (
          <div style={{ marginTop: '0.875rem', paddingTop: '0.875rem', borderTop: '1px solid var(--glass-border)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ color: 'var(--outline)', fontSize: '0.72rem', fontFamily: font }}>Delete?</span>
            <button onClick={handleDelete} disabled={deleting} style={{ background: 'rgba(238,125,119,0.12)', border: '1px solid rgba(238,125,119,0.25)', borderRadius: 3, cursor: 'pointer', padding: '0.25rem 0.5rem' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#ee7d77' }}>check</span>
            </button>
            <button onClick={() => setConfirmDelete(false)} style={{ background: 'transparent', border: '1px solid var(--glass-border)', borderRadius: 3, cursor: 'pointer', padding: '0.25rem 0.5rem' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 13, color: 'var(--outline)' }}>close</span>
            </button>
          </div>
        )}
        {!video.status?.match(/completed|failed/) && !confirmDelete && (
          <div style={{ paddingTop: '0.875rem', borderTop: '1px solid var(--glass-border)', display: 'flex', justifyContent: 'flex-end' }}>
            <button onClick={() => setConfirmDelete(true)} title="Delete" style={{ background: 'none', border: 'none', cursor: 'pointer', opacity: 0.45, transition: 'opacity 0.15s' }} onMouseEnter={e => e.currentTarget.style.opacity = '1'} onMouseLeave={e => e.currentTarget.style.opacity = '0.45'}>
              <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#ee7d77' }}>delete</span>
            </button>
          </div>
        )}
      </div>
    </GlowCard>
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

  function handleDelete(videoId) {
    setVideos(prev => prev.filter(v => v.video_id !== videoId));
  }

  function handleRename(videoId, displayName) {
    setVideos(prev => prev.map(v => v.video_id === videoId ? { ...v, display_name: displayName } : v));
  }

  const filteredVideos = videos.filter(v => filter === 'all' || v.status === filter);
  const filters = ['all', 'completed', 'processing', 'failed'];

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
        <GlowCard style={{ padding: '1.75rem 2rem' }}>
          <p style={{ color: '#ee7d77', marginBottom: '1.25rem', fontFamily: font, fontSize: '0.875rem', fontWeight: 300 }}>Error loading videos: {error}</p>
          <GlassButton onClick={loadVideos} variant="secondary" size="sm">Try again</GlassButton>
        </GlowCard>
      </div>
    );
  }

  return (
    <div style={{ padding: '3.5rem 3rem', fontFamily: font }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '3rem', flexWrap: 'wrap', gap: '1.25rem' }}>
        <div>
          <p style={{ fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#767578', marginBottom: '1rem' }}>Library</p>
          <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(2rem, 4vw, 3rem)', color: 'var(--on-surface)', letterSpacing: '0.03em' }}>Recent Captures</h1>
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
            padding: '0.4rem 1rem', borderRadius: 3,
            fontSize: '0.72rem', fontWeight: 300, cursor: 'pointer',
            transition: 'all 0.2s cubic-bezier(0.2,0,0,1)', fontFamily: font, letterSpacing: '0.1em', textTransform: 'uppercase',
            background: filter === f ? 'rgba(198,198,200,0.08)' : 'transparent',
            border: filter === f ? '1px solid rgba(198,198,200,0.2)' : '1px solid rgba(72,72,75,0.25)',
            color: filter === f ? '#b8b9bb' : '#767578',
          }}>
            {f} ({videos.filter(v => f === 'all' || v.status === f).length})
          </button>
        ))}
      </div>

      {/* Grid */}
      {filteredVideos.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '6rem 0' }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, color: 'var(--outline-faint)', display: 'block', marginBottom: '1.75rem', fontVariationSettings: "'FILL' 0, 'wght' 200" }}>video_library</span>
          <h3 style={{ fontFamily: font, color: 'var(--on-muted)', fontWeight: 300, fontSize: '1.1rem', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>No captures</h3>
          <p style={{ color: 'var(--outline)', marginBottom: '2.5rem', fontFamily: font, fontSize: '0.875rem', fontWeight: 300 }}>
            {filter === 'all' ? 'Import a video to get started.' : `No ${filter} videos found.`}
          </p>
          <Link href="/upload"><GlassButton>Import Media</GlassButton></Link>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.25rem' }}>
          {filteredVideos.map(video => (
            <VideoCard key={video.video_id} video={video} onDelete={handleDelete} onRename={handleRename} />
          ))}
        </div>
      )}
    </div>
  );
}
