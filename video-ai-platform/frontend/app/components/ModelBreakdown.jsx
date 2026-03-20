/**
 * Complete ModelBreakdown Component - WITH AUDIO ANALYSIS
 * Tracks all 14 AI models in the detection stack
 */

'use client';

export default function ModelBreakdown({ detections, video, audio_analysis }) {
  // Debug: Log to see what we're getting
  console.log('ModelBreakdown received:', { 
    detectionsCount: detections?.length, 
    firstDetection: detections?.[0],
    hasModelSource: detections?.[0]?.model_source,
    hasAudio: !!audio_analysis,
    audioKeys: audio_analysis ? Object.keys(audio_analysis) : []
  });

  if (!detections || detections.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-6">
        <p className="text-yellow-800">⚠️ No detections available to analyze</p>
      </div>
    );
  }

  // ALL 14 MODEL CONFIGURATIONS (Visual + Audio)
  const MODEL_CONFIG = {
    // VISUAL MODELS
    'ensemble_wbf': {
      name: 'Ensemble WBF',
      category: 'Visual Detection',
      icon: '🎯',
      color: 'blue',
      description: 'YOLOv11x+10x+9c fused detection',
      priority: 1
    },
    'yolov11x': {
      name: 'YOLOv11x',
      category: 'Visual Detection',
      icon: '🎯',
      color: 'blue',
      description: 'Primary object detection (93.5% accuracy)',
      priority: 1
    },
    'yolov11x-pose': {
      name: 'YOLOv11x-Pose',
      category: 'Visual Detection',
      icon: '🤸',
      color: 'cyan',
      description: 'Human pose & activity (17 keypoints)',
      priority: 2
    },
    'yolov11x-seg': {
      name: 'YOLOv11x-Seg',
      category: 'Visual Detection',
      icon: '✂️',
      color: 'teal',
      description: 'Pixel-perfect segmentation',
      priority: 3
    },
    'yolov10x': {
      name: 'YOLOv10x',
      category: 'Ensemble',
      icon: '🔵',
      color: 'green',
      description: 'Ensemble validation (secondary)',
      priority: 4
    },
    'yolov9c': {
      name: 'YOLOv9c',
      category: 'Ensemble',
      icon: '🟣',
      color: 'purple',
      description: 'Ensemble validation (tertiary)',
      priority: 5
    },
    'sam2': {
      name: 'SAM2',
      category: 'Segmentation',
      icon: '🎨',
      color: 'pink',
      description: 'Meta ultra-precise segmentation',
      priority: 6
    },
    'clip': {
      name: 'CLIP',
      category: 'Scene Understanding',
      icon: '🖼️',
      color: 'yellow',
      description: 'OpenAI scene comprehension',
      priority: 7
    },
    
    // MOTION/TRACKING
    'optical_flow': {
      name: 'Optical Flow',
      category: 'Motion Tracking',
      icon: '🌊',
      color: 'sky',
      description: 'Motion vectors & speed',
      priority: 8
    },
    'bytetrack': {
      name: 'ByteTrack',
      category: 'Motion Tracking',
      icon: '🎯',
      color: 'violet',
      description: 'Object ID tracking',
      priority: 9
    },
  };

  // Calculate statistics for each visual model
  const getModelStats = () => {
    const stats = {};
    
    // Initialize all visual models
    Object.keys(MODEL_CONFIG).forEach(model => {
      stats[model] = {
        count: 0,
        objects: {},
        confidence_sum: 0,
        avg_confidence: 0
      };
    });

    // Count detections per model
    detections.forEach((det, index) => {
      const model = String(det.model_source || 'unknown').toLowerCase().trim();
      const className = String(det.class_name || 'unknown');
      const confidence = parseFloat(det.confidence) || 0;

      if (stats[model]) {
        stats[model].count++;
        stats[model].confidence_sum += confidence;
        
        if (!stats[model].objects[className]) {
          stats[model].objects[className] = 0;
        }
        stats[model].objects[className]++;
      } else {
        // Track unknown models
        if (!stats['unknown']) {
          stats['unknown'] = {
            count: 0,
            objects: {},
            confidence_sum: 0,
            avg_confidence: 0
          };
        }
        stats['unknown'].count++;
      }
    });

    // Calculate average confidence
    Object.keys(stats).forEach(model => {
      if (stats[model].count > 0) {
        stats[model].avg_confidence = stats[model].confidence_sum / stats[model].count;
      }
    });

    return stats;
  };

  const stats = getModelStats();
  const totalDetections = detections.length;
  const activeModels = Object.keys(stats).filter(k => stats[k].count > 0 && k !== 'unknown').length;

  // Group visual models by category
  const categories = {
    'Visual Detection': [],
    'Ensemble': [],
    'Segmentation': [],
    'Scene Understanding': [],
    'Motion Tracking': []
  };

  Object.entries(MODEL_CONFIG).forEach(([key, config]) => {
    if (stats[key] && stats[key].count > 0) {
      categories[config.category].push({
        key,
        config,
        stats: stats[key]
      });
    }
  });

  // Remove empty categories
  Object.keys(categories).forEach(cat => {
    if (categories[cat].length === 0) {
      delete categories[cat];
    }
  });

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mt-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-2">
        🔬 Complete Detection Stack Analysis
      </h2>
      <p className="text-gray-600 mb-6">
        Visual + Audio analysis from 14 AI models
      </p>

      {/* Summary Stats */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 mb-6 border border-blue-200">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-3xl font-bold text-blue-600">{totalDetections}</p>
            <p className="text-xs text-gray-600">Total Detections</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-green-600">{activeModels}</p>
            <p className="text-xs text-gray-600">Active Visual Models</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-purple-600">
              {audio_analysis ? '4' : '0'}
            </p>
            <p className="text-xs text-gray-600">Audio Models</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-indigo-600">
              {video?.metadata?.duration?.toFixed(1) || 'N/A'}s
            </p>
            <p className="text-xs text-gray-600">Video Duration</p>
          </div>
        </div>
      </div>

      {/* Visual Models by Category */}
      {Object.entries(categories).map(([category, models]) => (
        <div key={category} className="mb-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center border-b pb-2">
            <span className="mr-2">
              {category === 'Visual Detection' && '👁️'}
              {category === 'Ensemble' && '🎯'}
              {category === 'Segmentation' && '✂️'}
              {category === 'Scene Understanding' && '🖼️'}
              {category === 'Motion Tracking' && '🌊'}
            </span>
            {category}
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map(({ key, config, stats: modelStats }) => {
              const percentage = ((modelStats.count / totalDetections) * 100).toFixed(1);
              const topObjects = Object.entries(modelStats.objects)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 3);

              return (
                <div 
                  key={key}
                  className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 hover:shadow-md transition"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl">{config.icon}</span>
                    <span className="text-sm font-semibold text-blue-700 bg-blue-100 px-2 py-1 rounded">
                      {percentage}%
                    </span>
                  </div>

                  <h4 className="font-bold text-gray-800 mb-1">
                    {config.name}
                  </h4>
                  <p className="text-xs text-gray-600 mb-3">
                    {config.description}
                  </p>

                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Detections:</span>
                      <span className="font-semibold text-gray-800">
                        {modelStats.count}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Avg Confidence:</span>
                      <span className="font-semibold text-gray-800">
                        {(modelStats.avg_confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {topObjects.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs text-gray-600 mb-1">Top detections:</p>
                      <div className="flex flex-wrap gap-1">
                        {topObjects.map(([obj, count]) => (
                          <span 
                            key={obj}
                            className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded"
                          >
                            {obj} ({count})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* ✅ NEW: Audio Analysis Section */}
      {audio_analysis && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center border-b pb-2">
            <span className="mr-2">🎤</span>
            Audio Analysis
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Whisper */}
            {audio_analysis.transcript && (
              <div className="bg-indigo-50 border-2 border-indigo-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">🎤</span>
                  <span className="text-xs font-semibold text-indigo-700 bg-indigo-100 px-2 py-1 rounded">
                    Active
                  </span>
                </div>
                <h4 className="font-bold text-gray-800 mb-1">Whisper</h4>
                <p className="text-xs text-gray-600 mb-3">
                  Speech transcription (99 languages)
                </p>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Segments:</span>
                    <span className="font-semibold text-gray-800">
                      {audio_analysis.transcript.segments?.length || 0}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Words:</span>
                    <span className="font-semibold text-gray-800">
                      {audio_analysis.transcript.text?.split(' ').length || 0}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Wav2Vec2 */}
            {audio_analysis.wav2vec2_classifications && (
              <div className="bg-fuchsia-50 border-2 border-fuchsia-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">🔊</span>
                  <span className="text-xs font-semibold text-fuchsia-700 bg-fuchsia-100 px-2 py-1 rounded">
                    Active
                  </span>
                </div>
                <h4 className="font-bold text-gray-800 mb-1">Wav2Vec2</h4>
                <p className="text-xs text-gray-600 mb-3">
                  Audio feature extraction
                </p>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Analyses:</span>
                    <span className="font-semibold text-gray-800">
                      {audio_analysis.wav2vec2_classifications.length}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Audio Events */}
            {audio_analysis.audio_events && (
              <div className="bg-rose-50 border-2 border-rose-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">⚡</span>
                  <span className="text-xs font-semibold text-rose-700 bg-rose-100 px-2 py-1 rounded">
                    Active
                  </span>
                </div>
                <h4 className="font-bold text-gray-800 mb-1">Audio Events</h4>
                <p className="text-xs text-gray-600 mb-3">
                  Event detection (8 categories)
                </p>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Events:</span>
                    <span className="font-semibold text-gray-800">
                      {audio_analysis.audio_events.length}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Audio-Visual Fusion */}
            {audio_analysis.fused_data && (
              <div className="bg-amber-50 border-2 border-amber-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">🔗</span>
                  <span className="text-xs font-semibold text-amber-700 bg-amber-100 px-2 py-1 rounded">
                    Active
                  </span>
                </div>
                <h4 className="font-bold text-gray-800 mb-1">Audio-Visual Fusion</h4>
                <p className="text-xs text-gray-600 mb-3">
                  Timeline synchronization
                </p>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Moments:</span>
                    <span className="font-semibold text-gray-800">
                      {audio_analysis.fused_data.timeline?.length || 0}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Models NOT Contributing */}
      {activeModels > 0 && Object.keys(MODEL_CONFIG).filter(k => stats[k].count === 0).length > 0 && (
        <div className="mt-6 bg-gray-50 rounded-lg p-4 border border-gray-200">
          <h4 className="font-semibold text-gray-700 mb-2 flex items-center">
            <span className="mr-2">⚠️</span>
            Visual Models Not Contributing
          </h4>
          <div className="flex flex-wrap gap-2">
            {Object.keys(MODEL_CONFIG)
              .filter(k => stats[k].count === 0)
              .map(key => (
                <span 
                  key={key}
                  className="text-sm bg-gray-200 text-gray-700 px-3 py-1 rounded"
                >
                  {MODEL_CONFIG[key].icon} {MODEL_CONFIG[key].name}
                </span>
              ))}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            These visual models are installed but didn't contribute detections to this video
          </p>
        </div>
      )}

      {/* No Audio Analysis Warning */}
      {!audio_analysis && (
        <div className="mt-6 bg-yellow-50 rounded-lg p-4 border border-yellow-200">
          <h4 className="font-semibold text-yellow-800 mb-2">
            ⚠️ No Audio Analysis Available
          </h4>
          <p className="text-sm text-yellow-700">
            This video was processed without audio analysis or has no audio track.
          </p>
        </div>
      )}
    </div>
  );
}