/**
 * Complete API client for all backend endpoints
 * Includes upload functions and video/detection functions
 */
import { fetchAuthSession } from 'aws-amplify/auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

/**
 * Get authentication token from Amplify session
 */
async function getAuthToken() {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    
    if (!token) {
      throw new Error('Not authenticated');
    }
    
    return token;
  } catch (error) {
    console.error('Error getting auth token:', error);
    throw error;
  }
}

// ============================================
// UPLOAD FUNCTIONS (for VideoUpload component)
// ============================================

/**
 * Get pre-signed URL for video upload
 */
export async function getPresignedUploadUrl(filename, contentType) {
  const token = await getAuthToken();
  
  const response = await fetch(`${API_BASE_URL}/upload/get-presigned-url`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      filename,
      content_type: contentType,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to get upload URL: ${errorText}`);
  }

  return response.json();
}

/**
 * Confirm video upload completion
 */
export async function confirmUpload(fileKey) {
  const token = await getAuthToken();
  
  const response = await fetch(`${API_BASE_URL}/upload/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ file_key: fileKey }),
  });

  if (!response.ok) {
    throw new Error('Failed to confirm upload');
  }

  return response.json();
}

// ============================================
// VIDEO FUNCTIONS (for video list/details)
// ============================================

/**
 * List all videos for the current user
 */
export async function listVideos() {
  const token = await getAuthToken();
  
  const response = await fetch(`${API_BASE_URL}/videos/`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch videos: ${response.status}`);
  }

  return response.json();
}

/**
 * Get detailed information about a specific video
 */
export async function getVideoDetails(videoId) {
  const token = await getAuthToken();
  
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Video not found');
    }
    throw new Error(`Failed to fetch video: ${response.status}`);
  }

  return response.json();
}

/**
 * Get video processing status (lightweight)
 */
export async function getVideoStatus(videoId) {
  const token = await getAuthToken();
  
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/status`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch status: ${response.status}`);
  }

  return response.json();
}

/**
 * Delete a video
 */
export async function deleteVideo(videoId) {
  const token = await getAuthToken();
  
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to delete video: ${response.status}`);
  }

  return response.json();
}

/**
 * Rename a video (set display_name)
 */
export async function renameVideo(videoId, displayName) {
  const token = await getAuthToken();
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/rename`, {
    method: 'PATCH',
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ display_name: displayName }),
  });
  if (!response.ok) throw new Error(`Rename failed: ${response.status}`);
  return response.json();
}

/**
 * Get presigned thumbnail URL for a video.
 * If no thumbnail exists yet, triggers on-demand generation from the source video.
 */
export async function getThumbnailUrl(videoId) {
  const token = await getAuthToken();

  // 1. Try existing thumbnail
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/thumbnail`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (response.ok) {
    const data = await response.json();
    return data.thumbnail_url;
  }

  // 2. If not found, generate on-demand (ffmpeg streams from S3 presigned URL)
  if (response.status === 404) {
    try {
      const genResponse = await fetch(`${API_BASE_URL}/videos/${videoId}/thumbnail/generate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (genResponse.ok) {
        const data = await genResponse.json();
        return data.thumbnail_url;
      }
    } catch {
      // generation failed — return null so the placeholder icon shows
    }
  }

  return null;
}

/**
 * Get the full raw worker stdout log for a video (saved to S3 during processing)
 */
export async function getVideoRawLog(videoId) {
  const token = await getAuthToken();
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/raw-log`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!response.ok) return null;
  const data = await response.json();
  return data.log || null;
}

/**
 * Get processing logs for a specific video
 */
export async function getVideoLogs(videoId) {
  const token = await getAuthToken();
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/logs`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(`Failed to fetch logs: ${response.status}`);
  return response.json();
}

/**
 * Get processing logs for all videos (system status)
 */
export async function getSystemLogs() {
  const token = await getAuthToken();
  const response = await fetch(`${API_BASE_URL}/videos/system/logs`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(`Failed to fetch system logs: ${response.status}`);
  return response.json();
}

/**
 * Get presigned URL for video playback
 */
export async function getVideoUrl(videoId) {
  try {
    const session = await fetchAuthSession();
    const userId = session.tokens?.idToken?.payload?.sub;
    
    if (!userId) {
      throw new Error('User ID not found in session');
    }

    // IMPORTANT: Use /api/videos/ NOT /api/api/videos/
    // The API_BASE_URL already includes the /api prefix if needed
    const url = `${API_BASE_URL}/videos/${videoId}/url?user_id=${userId}`;
    
    console.log('Fetching video URL from:', url);

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.tokens.idToken.toString()}`
      }
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get video URL');
    }

    const data = await response.json();
    console.log('✓ Got video URL');
    return data.video_url;
  } catch (error) {
    console.error('Error getting video URL:', error);
    throw error;
  }
}