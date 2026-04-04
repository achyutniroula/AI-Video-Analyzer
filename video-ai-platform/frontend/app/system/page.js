'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from 'aws-amplify/auth';
import { getSystemLogs, getVideoRawLog } from '../lib/api';
import { GlowCard } from '@/components/ui/spotlight-card';
import Sidebar from '../components/Sidebar';
import Footer from '../components/Footer';

const font = "'Manrope', sans-serif";

// ── Terminal line colorizer ───────────────────────────────────────────────────

function lineColor(line) {
  if (/✓/.test(line))                          return '#6ee7b7';
  if (/✗|ERROR|Error|FAILED|failed/.test(line)) return '#f0847e';
  if (/WARNING|Warning|warn/.test(line))        return '#e8c77a';
  if (/^={3,}|-{3,}/.test(line.trim()))        return '#48484b';
  if (/^\[INFO\]/.test(line))                   return '#acaaae';
  if (/^\[WARNING\]/.test(line))                return '#e8c77a';
  if (/^\[ERROR\]/.test(line))                  return '#f0847e';
  if (/Loading |Checkpoint |FutureWarning|UserWarning|tokenizers/.test(line)) return '#3a3a3d';
  return '#c6c6c8';
}

function TerminalLog({ text }) {
  const lines = text.split('\n');
  return (
    <div style={{
      background: 'rgba(5,5,6,0.85)',
      border: '1px solid rgba(72,72,75,0.25)',
      borderRadius: 6,
      padding: '1rem 1.25rem',
      maxHeight: 480,
      overflowY: 'auto',
      fontFamily: 'monospace',
      fontSize: '0.72rem',
      lineHeight: 1.7,
    }}>
      {lines.map((line, i) => (
        <div key={i} style={{ color: lineColor(line), whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {line || '\u00a0'}
        </div>
      ))}
    </div>
  );
}

// ── Per-video card ────────────────────────────────────────────────────────────

function VideoLogCard({ video }) {
  const [open, setOpen] = useState(false);
  const [rawLog, setRawLog] = useState(null);   // null = not loaded, '' = loaded but empty
  const [logLoading, setLogLoading] = useState(false);

  const logs = video.processing_logs || [];
  const hasRawLog = video.has_raw_log;
  const hasError = logs.some(l => l.level === 'ERROR');
  const hasWarning = logs.some(l => l.level === 'WARNING');
  const statusColor = hasError ? '#f0847e' : hasWarning ? '#e8c77a' : '#6ee7b7';

  async function loadRawLog() {
    if (rawLog !== null || logLoading) return;
    setLogLoading(true);
    try {
      const log = await getVideoRawLog(video.video_id);
      setRawLog(log ?? '');
    } catch {
      setRawLog('');
    } finally {
      setLogLoading(false);
    }
  }

  function handleToggle() {
    const next = !open;
    setOpen(next);
    if (next && hasRawLog && rawLog === null) loadRawLog();
  }

  function formatTs(ts) {
    if (!ts) return '—';
    try { return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }); }
    catch { return ts; }
  }

  return (
    <GlowCard style={{ padding: '1.5rem 1.75rem' }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', cursor: 'pointer', userSelect: 'none' }} onClick={handleToggle}>
        <span className="material-symbols-outlined" style={{ fontSize: 16, color: statusColor, flexShrink: 0, fontVariationSettings: "'FILL' 0, 'wght' 300" }}>
          {hasError ? 'error' : hasWarning ? 'warning' : 'check_circle'}
        </span>

        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ color: 'var(--on-surface)', fontSize: '0.825rem', fontWeight: 300, fontFamily: font, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '0.2rem' }}>
            {video.display_name || video.video_id}
          </p>
          {video.display_name && video.display_name !== video.video_id && (
            <p style={{ color: 'var(--outline-dim)', fontSize: '0.65rem', fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{video.video_id}</p>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', flexShrink: 0 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
            background: video.status === 'completed' ? 'rgba(110,231,183,0.06)' : video.status === 'failed' ? 'rgba(238,125,119,0.06)' : 'rgba(172,170,174,0.06)',
            border: `1px solid ${video.status === 'completed' ? 'rgba(110,231,183,0.2)' : video.status === 'failed' ? 'rgba(238,125,119,0.2)' : 'rgba(172,170,174,0.2)'}`,
            color: video.status === 'completed' ? '#6ee7b7' : video.status === 'failed' ? '#f0847e' : '#acaaae',
            fontSize: '0.65rem', fontWeight: 300, padding: '0.15rem 0.6rem', borderRadius: 2,
            textTransform: 'capitalize', letterSpacing: '0.08em', fontFamily: font,
          }}>
            {video.status}
          </span>
          {hasRawLog ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--outline)', fontSize: '0.65rem', fontFamily: font }}>
              <span className="material-symbols-outlined" style={{ fontSize: 12 }}>terminal</span>
              Full log
            </span>
          ) : (
            <span style={{ color: 'var(--outline-dim)', fontSize: '0.65rem', fontFamily: font }}>{logs.length} entries</span>
          )}
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--outline-dim)', transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>expand_more</span>
        </div>
      </div>

      {/* Expanded content */}
      {open && (
        <div style={{ marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid rgba(72,72,75,0.15)' }}>

          {/* Raw log (full terminal output) */}
          {hasRawLog && (
            <>
              {logLoading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--outline)', fontSize: '0.78rem', fontFamily: font, marginBottom: '1rem' }}>
                  <div style={{ width: 14, height: 14, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
                  Loading full log...
                </div>
              )}
              {!logLoading && rawLog && <TerminalLog text={rawLog} />}
              {!logLoading && rawLog === '' && (
                <p style={{ color: 'var(--outline-dim)', fontSize: '0.8rem', fontFamily: font, fontWeight: 300 }}>Log file is empty.</p>
              )}
            </>
          )}

          {/* Structured logs fallback (for videos without raw logs) */}
          {!hasRawLog && (
            logs.length === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <p style={{ color: 'var(--outline-dim)', fontSize: '0.8rem', fontFamily: font, fontWeight: 300 }}>
                  No logs recorded — this video was processed before worker logging was enabled.
                </p>
                {/* Show what we know from DynamoDB */}
                {(video.status || video.created_at || video.processed_at) && (
                  <div style={{ background: 'rgba(198,198,200,0.02)', border: '1px solid rgba(72,72,75,0.15)', borderRadius: 5, padding: '1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {video.created_at && <span style={{ color: 'var(--outline)', fontSize: '0.75rem', fontFamily: 'monospace' }}>Uploaded:   {new Date(video.created_at).toLocaleString()}</span>}
                    {video.processed_at && <span style={{ color: '#6ee7b7', fontSize: '0.75rem', fontFamily: 'monospace' }}>Completed:  {new Date(video.processed_at).toLocaleString()}</span>}
                    {video.error_message && <span style={{ color: '#f0847e', fontSize: '0.75rem', fontFamily: 'monospace' }}>Error:      {video.error_message}</span>}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {logs.map((log, i) => (
                  <div key={i} style={{ display: 'flex', gap: '0.875rem', alignItems: 'flex-start' }}>
                    <span style={{ color: 'var(--outline-dim)', fontSize: '0.65rem', fontFamily: 'monospace', width: 60, flexShrink: 0, paddingTop: 2 }}>{formatTs(log.timestamp)}</span>
                    <span style={{
                      display: 'inline-block', flexShrink: 0, width: 52, textAlign: 'center',
                      background: log.level === 'ERROR' ? 'rgba(238,125,119,0.08)' : log.level === 'WARNING' ? 'rgba(232,199,122,0.08)' : 'rgba(172,170,174,0.06)',
                      border: `1px solid ${log.level === 'ERROR' ? 'rgba(238,125,119,0.25)' : log.level === 'WARNING' ? 'rgba(232,199,122,0.25)' : 'rgba(172,170,174,0.2)'}`,
                      color: log.level === 'ERROR' ? '#f0847e' : log.level === 'WARNING' ? '#e8c77a' : '#acaaae',
                      fontSize: '0.6rem', fontWeight: 300, padding: '0.1rem 0.4rem', borderRadius: 2,
                      textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: font,
                    }}>{log.level}</span>
                    <span style={{ color: 'var(--outline)', fontSize: '0.72rem', fontFamily: 'monospace', width: 72, flexShrink: 0, paddingTop: 2 }}>{log.step}</span>
                    <span style={{ color: log.level === 'ERROR' ? '#f0847e' : log.level === 'WARNING' ? '#e8c77a' : 'var(--on-muted)', fontSize: '0.78rem', fontFamily: font, fontWeight: 300, lineHeight: 1.6, flex: 1 }}>{log.message}</span>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      )}
    </GlowCard>
  );

  function formatTs(ts) {
    if (!ts) return '—';
    try { return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }); }
    catch { return ts; }
  }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SystemPage() {
  const router = useRouter();
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getCurrentUser()
      .then(() => loadLogs())
      .catch(() => router.push('/login'));
  }, []);

  async function loadLogs() {
    try {
      setLoading(true);
      setError(null);
      const data = await getSystemLogs();
      const sorted = (data.videos || []).sort((a, b) =>
        (b.created_at || '').localeCompare(a.created_at || '')
      );
      setVideos(sorted);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const totalVideos = videos.length;
  const completed   = videos.filter(v => v.status === 'completed').length;
  const failed      = videos.filter(v => v.status === 'failed').length;
  const processing  = videos.filter(v => v.status === 'processing').length;

  if (loading) {
    return (
      <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', fontFamily: font }}>
        <Sidebar />
        <main style={{ marginLeft: 256, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite' }} />
          <p style={{ color: '#767578', fontFamily: font, fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.05em' }}>Loading system logs...</p>
        </main>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)', fontFamily: font }}>
      <Sidebar />

      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-10%', right: '-5%', width: '45%', height: '45%', borderRadius: '50%', background: 'rgba(198,198,200,0.02)', filter: 'blur(120px)' }} />
      </div>

      <main style={{ marginLeft: 256, flex: 1, padding: '3.5rem 3rem 5rem', position: 'relative', zIndex: 1 }}>

        <p style={{ fontSize: '0.65rem', fontWeight: 300, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#767578', marginBottom: '1.25rem' }}>
          System / Worker Logs
        </p>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ fontFamily: font, fontWeight: 200, fontSize: 'clamp(1.4rem, 3vw, 2rem)', color: 'var(--on-surface)', letterSpacing: '0.02em', marginBottom: '0.375rem' }}>
              System Logs
            </h1>
            <p style={{ color: 'var(--outline)', fontSize: '0.825rem', fontWeight: 300, fontFamily: font }}>
              Full worker output for every video — click a row to expand its log
            </p>
          </div>
          <button
            onClick={loadLogs}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              background: 'var(--glass-bg)', border: '1px solid var(--glass-border)',
              borderRadius: 6, color: 'var(--on-muted)', fontSize: '0.78rem',
              fontWeight: 300, padding: '0.6rem 1.125rem', cursor: 'pointer',
              fontFamily: font, letterSpacing: '0.08em', transition: 'all 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--on-surface)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--on-muted)'}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 15 }}>refresh</span>
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          {[
            { label: 'Total Videos', value: totalVideos, icon: 'movie',             color: 'var(--on-muted)' },
            { label: 'Completed',    value: completed,   icon: 'check_circle',      color: '#6ee7b7' },
            { label: 'Processing',   value: processing,  icon: 'progress_activity', color: '#acaaae' },
            { label: 'Failed',       value: failed,      icon: 'error',             color: '#f0847e' },
          ].map(stat => (
            <GlowCard key={stat.label} style={{ padding: '1.25rem 1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.625rem' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: stat.color, fontVariationSettings: "'FILL' 0, 'wght' 300" }}>{stat.icon}</span>
                <span style={{ fontSize: '0.6rem', fontWeight: 300, textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--outline-dim)', fontFamily: font }}>{stat.label}</span>
              </div>
              <p style={{ color: stat.color, fontSize: '1.75rem', fontWeight: 200, fontFamily: font, letterSpacing: '0.04em', lineHeight: 1 }}>{stat.value}</p>
            </GlowCard>
          ))}
        </div>

        {error && (
          <GlowCard style={{ padding: '1.5rem 1.75rem', marginBottom: '1.5rem', border: '1px solid rgba(238,125,119,0.2)' }}>
            <p style={{ color: '#f0847e', fontFamily: font, fontWeight: 300, fontSize: '0.875rem' }}>Failed to load logs: {error}</p>
          </GlowCard>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          {videos.length === 0 && !error && (
            <GlowCard style={{ padding: '2.5rem', textAlign: 'center' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 32, color: 'var(--outline-dim)', display: 'block', marginBottom: '0.75rem' }}>monitoring</span>
              <p style={{ color: 'var(--outline)', fontFamily: font, fontWeight: 300 }}>No videos processed yet.</p>
            </GlowCard>
          )}
          {videos.map(video => (
            <VideoLogCard key={video.video_id} video={video} />
          ))}
        </div>

        <Footer />
      </main>
    </div>
  );
}
