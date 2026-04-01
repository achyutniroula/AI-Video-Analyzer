'use client';

import { useState, useRef } from 'react';
import { getPresignedUploadUrl, confirmUpload } from '../lib/api';
import { GlowCard } from '@/components/ui/spotlight-card';
import { GlassButton } from '@/components/ui/liquid-glass-button';
import Link from 'next/link';

const font = "'Manrope', sans-serif";

export default function VideoUpload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [videoId, setVideoId] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleFileSelect = (selectedFile) => {
    if (!selectedFile) return;
    if (!selectedFile.type.startsWith('video/')) { setMessage('error:Please select a video file'); return; }
    if (selectedFile.size > 500 * 1024 * 1024) { setMessage('error:File size must be less than 500 MB'); return; }
    setFile(selectedFile);
    setMessage('');
  };

  const handleInputChange = (e) => handleFileSelect(e.target.files[0]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files[0]);
  };

  const uploadToS3 = async (url, file) => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
      });
      xhr.addEventListener('load', () => { if (xhr.status === 200) resolve(); else reject(new Error(`Upload failed with status ${xhr.status}`)); });
      xhr.addEventListener('error', () => reject(new Error('Upload failed')));
      xhr.open('PUT', url);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });
  };

  const handleUpload = async () => {
    if (!file) { setMessage('error:Please select a file first'); return; }
    setUploading(true);
    setProgress(0);
    setMessage('info:Getting upload URL...');
    try {
      const { upload_url, file_key } = await getPresignedUploadUrl(file.name, file.type);
      setMessage('info:Uploading video...');
      await uploadToS3(upload_url, file);
      setMessage('info:Confirming upload...');
      const result = await confirmUpload(file_key);
      setVideoId(result.video_id);
      setMessage('success:Upload successful! Video is being processed.');
      setProgress(100);
    } catch (error) {
      setMessage('error:Upload failed: ' + error.message);
    } finally {
      setUploading(false);
    }
  };

  const isSuccess = message.startsWith('success:');
  const isError = message.startsWith('error:');
  const displayMessage = message.replace(/^(success|error|info):/, '');

  return (
    <div>
      <GlowCard style={{ padding: '2rem 2.25rem' }}>

        {/* Drop Zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => !uploading && inputRef.current?.click()}
          style={{
            border: `1px dashed ${dragOver ? 'rgba(198,198,200,0.4)' : file ? 'rgba(110,231,183,0.3)' : 'rgba(72,72,75,0.4)'}`,
            borderRadius: 6,
            padding: '3.5rem 2.5rem',
            textAlign: 'center',
            background: dragOver ? 'var(--glass-bg)' : 'var(--input-bg)',
            transition: 'all 0.25s cubic-bezier(0.2,0,0,1)',
            cursor: uploading ? 'default' : 'pointer',
            marginBottom: '1.75rem',
          }}
        >
          <input ref={inputRef} type="file" accept="video/*" onChange={handleInputChange} disabled={uploading} style={{ display: 'none' }} />

          {file ? (
            <div>
              <span className="material-symbols-outlined" style={{ fontSize: 44, color: '#6ee7b7', display: 'block', margin: '0 auto 1.25rem', fontVariationSettings: "'FILL' 0, 'wght' 200, 'GRAD' 0, 'opsz' 48" }}>movie</span>
              <p style={{ color: '#acaaae', fontWeight: 300, fontSize: '0.9rem', marginBottom: '0.375rem', fontFamily: font }}>{file.name}</p>
              <p style={{ color: '#767578', fontSize: '0.8rem', fontFamily: font, fontWeight: 300 }}>{(file.size / 1024 / 1024).toFixed(2)} MB · {file.type}</p>
              {!uploading && <p style={{ color: '#48484b', fontSize: '0.75rem', marginTop: '1rem', fontFamily: font, fontWeight: 300, letterSpacing: '0.08em' }}>Click to change file</p>}
            </div>
          ) : (
            <div>
              <span className="material-symbols-outlined" style={{ fontSize: 40, color: dragOver ? '#acaaae' : '#48484b', display: 'block', margin: '0 auto 1.25rem', fontVariationSettings: "'FILL' 0, 'wght' 200, 'GRAD' 0, 'opsz' 48', transition: 'color 0.2s'" }}>upload_file</span>
              <p style={{ color: '#acaaae', fontWeight: 300, fontSize: '0.95rem', marginBottom: '0.4rem', fontFamily: font, letterSpacing: '0.02em' }}>Drop your video here</p>
              <p style={{ color: '#767578', fontSize: '0.825rem', fontFamily: font, fontWeight: 300 }}>or click to browse</p>
              <p style={{ color: '#48484b', fontSize: '0.75rem', marginTop: '1rem', fontFamily: font, fontWeight: 300, letterSpacing: '0.08em', textTransform: 'uppercase' }}>MP4, MOV, AVI · Max 500 MB</p>
            </div>
          )}
        </div>

        {/* Progress bar */}
        {uploading && (
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ color: '#767578', fontSize: '0.78rem', fontFamily: font, fontWeight: 300, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Uploading</span>
              <span style={{ color: '#b8b9bb', fontSize: '0.78rem', fontWeight: 300, fontFamily: font }}>{progress}%</span>
            </div>
            <div style={{ width: '100%', height: 2, background: 'rgba(72,72,75,0.3)', borderRadius: 1, overflow: 'hidden' }}>
              <div style={{ width: `${progress}%`, height: '100%', background: 'linear-gradient(90deg, #454749, #c6c6c8)', borderRadius: 1, transition: 'width 0.3s ease' }} />
            </div>
          </div>
        )}

        {/* Message */}
        {message && (
          <div style={{ marginBottom: '1.5rem', padding: '0.75rem 1rem', borderRadius: 4, background: isSuccess ? 'rgba(52,211,153,0.05)' : isError ? 'rgba(238,125,119,0.05)' : 'rgba(198,198,200,0.04)', border: `1px solid ${isSuccess ? 'rgba(52,211,153,0.18)' : isError ? 'rgba(238,125,119,0.18)' : 'rgba(198,198,200,0.12)'}`, display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 15, color: isSuccess ? '#6ee7b7' : isError ? '#ee7d77' : '#acaaae', fontVariationSettings: "'FILL' 0, 'wght' 300" }}>
              {isSuccess ? 'check_circle' : isError ? 'error' : 'progress_activity'}
            </span>
            <span style={{ color: isSuccess ? '#6ee7b7' : isError ? '#ee7d77' : '#acaaae', fontSize: '0.825rem', fontFamily: font, fontWeight: 300 }}>{displayMessage}</span>
          </div>
        )}

        {/* Upload button */}
        <GlassButton
          onClick={handleUpload}
          disabled={!file || uploading}
          variant={!file || uploading ? 'secondary' : 'primary'}
          style={{ width: '100%', fontSize: '0.78rem' }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 15 }}>{uploading ? 'progress_activity' : 'upload'}</span>
          {uploading ? 'Uploading...' : 'Upload Video'}
        </GlassButton>
      </GlowCard>

      {/* Success link */}
      {videoId && (
        <div style={{ marginTop: '1.25rem', padding: '1.25rem 1.5rem', background: 'rgba(52,211,153,0.04)', border: '1px solid rgba(52,211,153,0.15)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <p style={{ color: '#6ee7b7', fontWeight: 300, marginBottom: '0.25rem', fontFamily: font, fontSize: '0.875rem', letterSpacing: '0.03em' }}>Processing started</p>
            <p style={{ color: '#48484b', fontSize: '0.75rem', fontFamily: 'monospace' }}>ID: {videoId}</p>
          </div>
          <Link href={`/videos/${videoId}`} style={{ color: '#b8b9bb', fontWeight: 300, fontSize: '0.78rem', border: '1px solid rgba(198,198,200,0.18)', padding: '0.45rem 1rem', borderRadius: 4, fontFamily: font, letterSpacing: '0.1em', textTransform: 'uppercase', transition: 'all 0.2s' }}>
            View →
          </Link>
        </div>
      )}
    </div>
  );
}
