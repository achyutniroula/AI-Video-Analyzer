'use client';

import { useEffect, useRef, useState } from 'react';
import { getVideoUrl } from '../lib/api';

const font = "'Manrope', sans-serif";

function getColorForClass(className) {
  const colors = { person: '#c6c6c8', car: '#9adbc8', truck: '#87ceeb', bus: '#dda0dd', motorcycle: '#f0e68c', bicycle: '#98d8c8', dog: '#f4a460', cat: '#87ceeb' };
  if (colors[className]) return colors[className];
  let hash = 0;
  for (let i = 0; i < className.length; i++) hash = className.charCodeAt(i) + ((hash << 5) - hash);
  return `hsl(${Math.abs(hash) % 360}, 35%, 72%)`;
}

export default function VideoPlayer({ video }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const progressRef = useRef(null);

  const [videoUrl, setVideoUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [currentDetections, setCurrentDetections] = useState([]);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [isSeeking, setIsSeeking] = useState(false);

  useEffect(() => { loadVideoUrl(); }, [video.video_id]);

  async function loadVideoUrl() {
    try {
      setLoading(true);
      setError(null);
      const url = await getVideoUrl(video.video_id);
      setVideoUrl(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!videoUrl || !videoRef.current || !canvasRef.current) return;
    const el = videoRef.current;
    const canvas = canvasRef.current;

    const onMeta = () => {
      canvas.width = el.videoWidth;
      canvas.height = el.videoHeight;
      setDuration(el.duration || 0);
    };

    el.addEventListener('loadedmetadata', onMeta);
    el.addEventListener('timeupdate', handleTimeUpdate);
    el.addEventListener('durationchange', () => setDuration(el.duration || 0));

    return () => {
      el.removeEventListener('loadedmetadata', onMeta);
      el.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [videoUrl, video.detections]);

  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = playbackSpeed;
  }, [playbackSpeed]);

  function handleTimeUpdate() {
    if (!videoRef.current) return;
    const el = videoRef.current;
    const fps = video.metadata?.fps || 25;
    const frame = Math.floor(el.currentTime * fps);
    setCurrentTime(el.currentTime);
    setCurrentFrame(frame);
    const dets = video.detections?.filter(d => d.frame === frame) || [];
    setCurrentDetections(dets);
    drawBoundingBoxes(dets);
  }

  function drawBoundingBoxes(detections) {
    const canvas = canvasRef.current;
    const el = videoRef.current;
    if (!canvas || !el) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    detections.forEach(d => {
      const b = d.bbox;
      const w = b.x2 - b.x1;
      const h = b.y2 - b.y1;
      const color = getColorForClass(d.class_name);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(b.x1, b.y1, w, h);
      const label = `${d.class_name} ${(d.confidence * 100).toFixed(0)}%`;
      ctx.font = '300 12px Manrope, sans-serif';
      const tw = ctx.measureText(label).width;
      ctx.fillStyle = color + 'bb';
      ctx.fillRect(b.x1, b.y1 - 18, tw + 8, 18);
      ctx.fillStyle = '#111';
      ctx.fillText(label, b.x1 + 4, b.y1 - 5);
    });
  }

  function togglePlay() {
    if (!videoRef.current) return;
    if (isPlaying) { videoRef.current.pause(); setIsPlaying(false); }
    else { videoRef.current.play(); setIsPlaying(true); }
  }

  function seekFrame(dir) {
    if (!videoRef.current) return;
    const fps = video.metadata?.fps || 25;
    videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime + dir * (1 / fps));
  }

  function handleProgressClick(e) {
    if (!videoRef.current || !progressRef.current) return;
    const rect = progressRef.current.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    videoRef.current.currentTime = pct * (videoRef.current.duration || 0);
  }

  function formatTime(s) {
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
  const speeds = [0.25, 0.5, 1, 1.5, 2];

  if (loading) {
    return (
      <div style={{ background: '#000', borderRadius: 6, overflow: 'hidden', aspectRatio: '16/9', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 24, height: 24, borderRadius: '50%', border: '1px solid rgba(198,198,200,0.4)', borderTopColor: 'transparent', animation: 'spin 0.9s linear infinite', margin: '0 auto 0.75rem' }} />
          <p style={{ color: '#767578', fontSize: '0.78rem', fontFamily: font, fontWeight: 300, letterSpacing: '0.06em' }}>Loading video...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ background: 'var(--surface-low)', border: '1px solid rgba(238,125,119,0.18)', borderRadius: 6, padding: '2.5rem', textAlign: 'center' }}>
        <span className="material-symbols-outlined" style={{ fontSize: 32, color: 'var(--error)', display: 'block', marginBottom: '0.75rem' }}>error_outline</span>
        <p style={{ color: 'var(--error)', fontSize: '0.825rem', fontFamily: font, fontWeight: 300, marginBottom: '1.25rem' }}>{error}</p>
        <button onClick={loadVideoUrl} style={{ color: 'var(--on-muted)', background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 4, padding: '0.4rem 1.25rem', cursor: 'pointer', fontSize: '0.72rem', fontFamily: font, fontWeight: 300, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Retry</button>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: font }}>

      {/* Video */}
      <div style={{ position: 'relative', background: '#000', borderRadius: '6px 6px 0 0', overflow: 'hidden', lineHeight: 0 }}>
        <video
          ref={videoRef}
          src={videoUrl}
          style={{ width: '100%', display: 'block' }}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
        />
        <canvas
          ref={canvasRef}
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
        />
      </div>

      {/* Controls */}
      <div style={{ background: 'var(--ctrl-bg)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', borderRadius: '0 0 6px 6px', padding: '0.75rem 1.125rem', border: '1px solid var(--outline-faint)', borderTop: 'none' }}>

        {/* Progress bar */}
        <div
          ref={progressRef}
          onClick={handleProgressClick}
          style={{ height: 3, background: 'rgba(72,72,75,0.45)', borderRadius: 2, cursor: 'pointer', marginBottom: '0.75rem', position: 'relative' }}
        >
          <div style={{ width: `${progress}%`, height: '100%', background: 'linear-gradient(90deg, #454749, #c6c6c8)', borderRadius: 2 }} />
          <div style={{ position: 'absolute', top: '50%', left: `${progress}%`, transform: 'translate(-50%, -50%)', width: 9, height: 9, borderRadius: '50%', background: '#c6c6c8', boxShadow: '0 0 5px rgba(198,198,200,0.6)', transition: 'left 0.1s linear' }} />
        </div>

        {/* Buttons row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>

          {/* Playback */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <button onClick={() => seekFrame(-1)} style={ctrlBtn} onMouseEnter={e => hoverOn(e)} onMouseLeave={e => hoverOff(e)}>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#767578' }}>skip_previous</span>
            </button>
            <button onClick={togglePlay} style={playBtn} onMouseEnter={e => { e.currentTarget.style.background = 'rgba(198,198,200,0.2)'; }} onMouseLeave={e => { e.currentTarget.style.background = 'rgba(198,198,200,0.1)'; }}>
              <span className="material-symbols-outlined" style={{ fontSize: 22, color: '#e7e5e8', fontVariationSettings: "'FILL' 1, 'wght' 400" }}>{isPlaying ? 'pause' : 'play_arrow'}</span>
            </button>
            <button onClick={() => seekFrame(1)} style={ctrlBtn} onMouseEnter={e => hoverOn(e)} onMouseLeave={e => hoverOff(e)}>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#767578' }}>skip_next</span>
            </button>
          </div>

          {/* Time */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: '#767578', fontSize: '0.72rem', fontFamily: 'monospace' }}>
            <span style={{ color: '#b8b9bb' }}>{formatTime(currentTime)}</span>
            <span style={{ color: '#2b2c2f' }}>/</span>
            <span>{formatTime(duration)}</span>
            <span style={{ color: '#2b2c2f', marginLeft: '0.5rem', fontFamily: font, fontSize: '0.65rem', letterSpacing: '0.05em' }}>F{currentFrame}</span>
          </div>

          {/* Speed */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
            {speeds.map(s => (
              <button key={s} onClick={() => setPlaybackSpeed(s)} style={{
                padding: '0.18rem 0.4rem', borderRadius: 3,
                background: playbackSpeed === s ? 'rgba(198,198,200,0.14)' : 'transparent',
                border: playbackSpeed === s ? '1px solid rgba(198,198,200,0.22)' : '1px solid transparent',
                color: playbackSpeed === s ? '#b8b9bb' : '#48484b',
                fontSize: '0.65rem', fontFamily: font, fontWeight: 300,
                cursor: 'pointer', letterSpacing: '0.03em',
                transition: 'all 0.15s',
              }}>
                {s}×
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Frame detections */}
      {currentDetections.length > 0 && (
        <div style={{ marginTop: '0.75rem', padding: '0.75rem 1rem', background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 6, backdropFilter: 'blur(12px)' }}>
          <p style={{ fontSize: '0.6rem', fontWeight: 300, textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--outline-dim)', marginBottom: '0.5rem', fontFamily: font }}>
            Frame {currentFrame} · {currentDetections.length} detection{currentDetections.length !== 1 ? 's' : ''}
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
            {currentDetections.map((d, i) => (
              <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 3, padding: '0.18rem 0.55rem', fontSize: '0.7rem', color: 'var(--on-muted)', fontFamily: font, fontWeight: 300 }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: getColorForClass(d.class_name), display: 'inline-block', flexShrink: 0 }} />
                {d.class_name} {(d.confidence * 100).toFixed(0)}%
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const ctrlBtn = {
  width: 30, height: 30, borderRadius: 4,
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(72,72,75,0.3)',
  cursor: 'pointer',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  transition: 'all 0.15s',
};

const playBtn = {
  width: 38, height: 38, borderRadius: 6,
  background: 'rgba(198,198,200,0.1)',
  border: '1px solid rgba(198,198,200,0.2)',
  cursor: 'pointer',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  transition: 'all 0.2s',
};

function hoverOn(e) { e.currentTarget.style.background = 'rgba(255,255,255,0.09)'; }
function hoverOff(e) { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }
