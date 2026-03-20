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

export default function VideoDetailPage() {
  const params = useParams();
  const router = useRouter();
  const videoId = params.video_id;
  
  const [video, setVideo] = useState(null);
  const [detections, setDetections] = useState([]);
  const [audioAnalysis, setAudioAnalysis] = useState(null); // ✅ NEW: Audio analysis state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  async function checkAuth() {
    try {
      await getCurrentUser();
      setAuthenticated(true);
      loadVideoDetails();
    } catch (error) {
      console.error('Not authenticated:', error);
      router.push('/login');
    }
  }

  // Calculate summary from detections if not provided by backend
  function calculateSummary(detections) {
    if (!detections || detections.length === 0) {
      return {
        total_detections: 0,
        by_class: {},
        unique_tracked_objects: 0
      };
    }

    const by_class = {};
    
    detections.forEach(detection => {
      const className = detection.class_name;
      by_class[className] = (by_class[className] || 0) + 1;
    });

    return {
      total_detections: detections.length,
      by_class: by_class,
      unique_tracked_objects: Object.keys(by_class).length
    };
  }

  async function loadVideoDetails() {
    try {
      setLoading(true);
      setError(null);
      console.log('Fetching video:', videoId);
      
      // Get auth token
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (!token) {
        throw new Error('No authentication token');
      }
      
      // Fetch video metadata
      const data = await getVideoDetails(videoId);
      console.log('Video data received:', data);
      console.log('Has summary?', !!data.summary);
      
      // ✅ FIX: Fetch detections separately from S3
      try {
        console.log('Fetching detections from /detections endpoint...');
        const detectionsRes = await fetch(
          `http://localhost:8000/api/videos/${videoId}/detections`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );
        
        if (detectionsRes.ok) {
          const detectionsData = await detectionsRes.json();
          console.log('✅ Detections loaded:', detectionsData.total_detections);
          console.log('First detection:', detectionsData.detections?.[0]);
          console.log('Has model_source?', detectionsData.detections?.[0]?.model_source);
          
          // ✅ NEW: Check for audio_analysis
          console.log('Has audio_analysis?', !!detectionsData.audio_analysis);
          if (detectionsData.audio_analysis) {
            console.log('Audio analysis keys:', Object.keys(detectionsData.audio_analysis));
            setAudioAnalysis(detectionsData.audio_analysis);
          }
          
          setDetections(detectionsData.detections || []);
          
          // If no summary in DynamoDB, calculate from detections
          if (!data.summary && detectionsData.detections) {
            console.log('Calculating summary from detections...');
            data.summary = calculateSummary(detectionsData.detections);
          }
        } else {
          console.warn('Failed to load detections:', detectionsRes.status);
          setDetections([]);
        }
      } catch (detErr) {
        console.error('Error fetching detections:', detErr);
        setDetections([]);
      }
      
      setVideo(data);
    } catch (err) {
      console.error('Error loading video:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  }

  function formatTimestamp(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  function getTopObjects(summary) {
    if (!summary || !summary.by_class) return [];
    
    return Object.entries(summary.by_class)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([className, count]) => ({ className, count }));
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading video details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Video</h2>
          <p className="text-red-600">{error}</p>
          <div className="mt-4 flex gap-4">
            <button
              onClick={loadVideoDetails}
              className="text-red-600 hover:text-red-800 underline"
            >
              Try Again
            </button>
            <Link href="/videos" className="text-blue-600 hover:text-blue-800 underline">
              Back to Videos
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!video) return null;

  const topObjects = getTopObjects(video.summary);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Back Button */}
        <Link 
          href="/videos"
          className="inline-flex items-center text-blue-600 hover:text-blue-800 mb-6"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Videos
        </Link>

        {/* Page Title */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Video Details
          </h1>
          <p className="text-gray-600">Video ID: {video.video_id}</p>
        </div>

        {/* Video Information Card */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Video Information</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left Column */}
            <div className="space-y-3">
              <div>
                <span className="text-sm font-medium text-gray-500">Status:</span>
                <span className={`ml-2 px-3 py-1 text-sm rounded-full ${
                  video.status === 'completed' ? 'bg-green-100 text-green-800' :
                  video.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {video.status}
                </span>
              </div>
              
              <div>
                <span className="text-sm font-medium text-gray-500">Uploaded:</span>
                <span className="ml-2 text-sm text-gray-900">{formatDate(video.created_at)}</span>
              </div>
              
              <div>
                <span className="text-sm font-medium text-gray-500">Processed:</span>
                <span className="ml-2 text-sm text-gray-900">
                  {video.processed_at ? formatDate(video.processed_at) : 'N/A'}
                </span>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-3">
              {video.metadata && (
                <>
                  <div>
                    <span className="text-sm font-medium text-gray-500">Resolution:</span>
                    <span className="ml-2 text-sm text-gray-900">
                      {video.metadata.width} x {video.metadata.height}
                    </span>
                  </div>
                  
                  <div>
                    <span className="text-sm font-medium text-gray-500">Duration:</span>
                    <span className="ml-2 text-sm text-gray-900">
                      {video.metadata.duration?.toFixed(2)} seconds
                    </span>
                  </div>
                  
                  <div>
                    <span className="text-sm font-medium text-gray-500">FPS:</span>
                    <span className="ml-2 text-sm text-gray-900">
                      {video.metadata.fps?.toFixed(2)}
                    </span>
                  </div>
                  
                  <div>
                    <span className="text-sm font-medium text-gray-500">Total Frames:</span>
                    <span className="ml-2 text-sm text-gray-900">
                      {video.metadata.total_frames}
                    </span>
                  </div>
                  
                  <div>
                    <span className="text-sm font-medium text-gray-500">Frames Processed:</span>
                    <span className="ml-2 text-sm text-gray-900">
                      {video.metadata.frames_processed}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Video Player */}
        <VideoPlayer video={video} />

        {/* Detection Summary Card */}
        {video.summary && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Detection Summary</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Total Detections */}
              <div className="bg-blue-50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-blue-600">
                  {video.summary.total_detections || 0}
                </p>
                <p className="text-sm text-gray-600 mt-1">Total Detections</p>
              </div>

              {/* Unique Objects */}
              <div className="bg-green-50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-green-600">
                  {video.summary.unique_tracked_objects || 0}
                </p>
                <p className="text-sm text-gray-600 mt-1">Unique Objects</p>
              </div>

              {/* Frames Analyzed */}
              <div className="bg-purple-50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-purple-600">
                  {video.metadata?.frames_processed || 0}
                </p>
                <p className="text-sm text-gray-600 mt-1">Frames Analyzed</p>
              </div>
            </div>

            {/* Top 3 Objects */}
            {topObjects.length > 0 && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Top Detected Objects</h3>
                <div className="space-y-2">
                  {topObjects.map((obj, index) => (
                    <div key={obj.className} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center">
                        <span className="text-2xl font-bold text-gray-400 mr-4">
                          #{index + 1}
                        </span>
                        <span className="text-sm font-medium text-gray-900 capitalize">
                          {obj.className}
                        </span>
                      </div>
                      <span className="text-sm font-semibold text-blue-600">
                        {obj.count} detections
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Detection Charts */}
        <DetectionCharts video={video} />

        {/* ✅ FIXED: Pass audio_analysis to ModelBreakdown */}
        <ModelBreakdown 
          detections={detections} 
          video={video}
          audio_analysis={audioAnalysis}
        />

        {/* AI Video Narrative */}
        <VideoNarrative videoId={videoId} />

        {/* All Detections Table */}
        {detections && detections.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-6 mt-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              All Detections ({detections.length})
            </h2>
            
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Frame
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Object
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Confidence
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Model
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Position
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {detections.slice(0, 100).map((detection, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {detection.frame}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatTimestamp(detection.timestamp)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 capitalize">
                        {detection.class_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {(detection.confidence * 100).toFixed(1)}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500">
                        {detection.model_source || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ({detection.bbox.x1.toFixed(0)}, {detection.bbox.y1.toFixed(0)})
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {detections.length > 100 && (
              <p className="text-sm text-gray-500 mt-4 text-center">
                Showing first 100 of {detections.length} detections
              </p>
            )}
          </div>
        )}

      </div>
    </div>
  );
}