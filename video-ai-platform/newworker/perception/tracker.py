"""
ByteTracker — Multi-Object Tracker (CPU)

Associates detections across frames using IoU-based matching with a
simplified Kalman filter for motion prediction.  Tracks are assigned
stable integer IDs that persist across frames.

Based on the ByteTrack algorithm (Zhang et al., 2022):
  1. Separate detections by confidence into high / low sets
  2. Match high-confidence detections to existing tracks (IoU + Kalman)
  3. Match remaining tracks to low-confidence detections
  4. Initialize new tracks from unmatched high-conf detections
  5. Age out stale tracks

CPU only — no model weights needed.
VRAM: 0 MB
Time: ~0.01s per frame
"""

import time
from typing import Any, Dict, List, Optional

import numpy as np

from .base import BasePerceptionModule, PerceptionOutput


# ─────────────────────────────────────────────────────────────────────────────
#  Kalman Filter (linear constant-velocity, state = [x,y,w,h, vx,vy,vw,vh])
# ─────────────────────────────────────────────────────────────────────────────

class _KalmanBox:
    """Minimal Kalman filter for a bounding-box track."""

    _F = None   # transition matrix (shared)
    _H = None   # measurement matrix (shared)

    def __init__(self, bbox: List[float]):
        # State: [cx, cy, w, h, vcx, vcy, vw, vh]
        cx, cy, w, h = self._to_center(bbox)
        self.x = np.array([cx, cy, w, h, 0., 0., 0., 0.], dtype=np.float32)

        # Process / measurement noise
        self.P = np.eye(8, dtype=np.float32) * 10.0
        self.P[4:, 4:] *= 1000.0      # high uncertainty for initial velocities

        self.Q = np.eye(8, dtype=np.float32)
        self.Q[4:, 4:] *= 0.01

        self.R = np.eye(4, dtype=np.float32) * 1.0

        if _KalmanBox._F is None:
            F = np.eye(8, dtype=np.float32)
            F[0, 4] = F[1, 5] = F[2, 6] = F[3, 7] = 1.0
            _KalmanBox._F = F
            _KalmanBox._H = np.eye(4, 8, dtype=np.float32)

    def predict(self):
        self.x = _KalmanBox._F @ self.x
        self.P = _KalmanBox._F @ self.P @ _KalmanBox._F.T + self.Q
        return self._to_xyxy()

    def update(self, bbox: List[float]):
        z = np.array(self._to_center(bbox), dtype=np.float32)
        y = z - _KalmanBox._H @ self.x
        S = _KalmanBox._H @ self.P @ _KalmanBox._H.T + self.R
        K = self.P @ _KalmanBox._H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(8) - K @ _KalmanBox._H) @ self.P
        return self._to_xyxy()

    def _to_xyxy(self) -> List[float]:
        cx, cy, w, h = self.x[:4]
        return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]

    @staticmethod
    def _to_center(bbox):
        x1, y1, x2, y2 = bbox
        return (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1


# ─────────────────────────────────────────────────────────────────────────────
#  Track
# ─────────────────────────────────────────────────────────────────────────────

class _Track:
    _next_id = 1

    def __init__(self, detection: Dict):
        self.track_id = _Track._next_id
        _Track._next_id += 1
        self.label = detection["label"]
        self.bbox  = detection["bbox"]
        self.score = detection.get("coverage", 1.0)
        self.kf    = _KalmanBox(self.bbox)
        self.age   = 1
        self.hits  = 1
        self.time_since_update = 0

    def predict(self):
        self.bbox = self.kf.predict()
        self.age += 1
        self.time_since_update += 1

    def update(self, detection: Dict):
        self.bbox  = self.kf.update(detection["bbox"])
        self.score = detection.get("coverage", self.score)
        self.hits += 1
        self.time_since_update = 0

    def to_dict(self) -> Dict:
        bbox = [round(float(v), 1) for v in self.bbox]
        return {
            "track_id": self.track_id,
            "label": self.label,
            "bbox": bbox,
            "score": round(float(self.score), 4),
            "age": self.age,
            "hits": self.hits,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  ByteTracker perception module
# ─────────────────────────────────────────────────────────────────────────────

class ByteTracker(BasePerceptionModule):
    """
    IoU + Kalman multi-object tracker.

    Call with `panoptic_things` kwarg (list of thing dicts from Mask2Former).
    Internally maintains track state across frames — **do not re-instantiate
    between frames**; keep one ByteTracker instance alive for the whole video.

    Example:
        tracker = ByteTracker()
        tracker.load_model()

        for frame_id, frame, timestamp, things in pipeline:
            output = tracker(frame, frame_id=frame_id, timestamp=timestamp,
                             panoptic_things=things)
            tracks = output.data["tracks"]   # [{track_id, label, bbox}, ...]
    """

    HIGH_THRESH  = 0.05   # coverage above which a detection is "high confidence"
    LOW_THRESH   = 0.01   # minimum coverage to consider at all
    IOU_THRESH   = 0.30   # IoU to match detection → track
    MAX_AGE      = 30     # frames before a lost track is deleted

    def __init__(self, **kwargs):
        kwargs["device"] = "cpu"
        super().__init__(**kwargs)
        self._tracks: List[_Track] = []

    def reset(self):
        """Reset tracker state (call between videos)."""
        self._tracks = []
        _Track._next_id = 1

    def load_model(self):
        self.model = True   # sentinel
        print("✓ ByteTracker initialized (CPU, no model)")

    # ------------------------------------------------------------------ #
    #  Override __call__                                                   #
    # ------------------------------------------------------------------ #

    def __call__(
        self,
        frame: Any,
        frame_id: int,
        timestamp: float,
        panoptic_things: Optional[List[Dict]] = None,
        **kwargs,
    ) -> PerceptionOutput:
        t0 = time.time()
        detections = panoptic_things or []
        tracks = self._update(detections)

        return PerceptionOutput(
            module_name=self.name,
            timestamp=timestamp,
            frame_id=frame_id,
            data={
                "tracks": [t.to_dict() for t in tracks],
                "num_tracks": len(tracks),
            },
            metadata={"device": "cpu", "quantized": False},
            processing_time=time.time() - t0,
            gpu_memory_used=None,
        )

    # ------------------------------------------------------------------ #
    #  ByteTrack update logic                                              #
    # ------------------------------------------------------------------ #

    def _update(self, detections: List[Dict]) -> List[_Track]:
        # Split by confidence
        high = [d for d in detections if d.get("coverage", 0) >= self.HIGH_THRESH]
        low  = [d for d in detections if self.LOW_THRESH <= d.get("coverage", 0) < self.HIGH_THRESH]

        # Step 1: predict all existing tracks
        for t in self._tracks:
            t.predict()

        active = [t for t in self._tracks if t.time_since_update <= 1]
        lost   = [t for t in self._tracks if t.time_since_update > 1]

        # Step 2: match high-conf detections to active tracks
        matched_h, unmatched_tracks, unmatched_det_h = self._match(active, high)
        for ti, di in matched_h:
            active[ti].update(high[di])

        # Step 3: match lost tracks to low-conf detections
        remaining_lost = [active[i] for i in unmatched_tracks] + lost
        matched_l, still_lost, unmatched_det_l = self._match(remaining_lost, low)
        for ti, di in matched_l:
            remaining_lost[ti].update(low[di])

        # Step 4: new tracks from unmatched high-conf detections
        new_tracks = [_Track(high[i]) for i in unmatched_det_h]

        # Step 5: reassemble and age out dead tracks
        self._tracks = (
            [t for t in active if t.time_since_update == 0]          # matched active
            + [remaining_lost[i] for i, _ in matched_l]              # rescued lost
            + new_tracks                                               # newborn
            + [t for t in still_lost if t.age < self.MAX_AGE]        # still lost (keep)
        )

        return [t for t in self._tracks if t.hits >= 1]

    def _match(self, tracks, detections):
        if not tracks or not detections:
            return [], list(range(len(tracks))), list(range(len(detections)))

        iou_mat = np.zeros((len(tracks), len(detections)), dtype=np.float32)
        for i, t in enumerate(tracks):
            for j, d in enumerate(detections):
                iou_mat[i, j] = _iou_bbox(t.bbox, d["bbox"])

        # Greedy matching (sufficient for Phase 2; replace with Hungarian if needed)
        matched, unmatched_t, unmatched_d = [], set(range(len(tracks))), set(range(len(detections)))
        rows, cols = np.where(iou_mat >= self.IOU_THRESH)
        used_t, used_d = set(), set()
        # Sort by IoU descending
        order = np.argsort(-iou_mat[rows, cols])
        for k in order:
            ti, di = int(rows[k]), int(cols[k])
            if ti not in used_t and di not in used_d:
                matched.append((ti, di))
                used_t.add(ti); used_d.add(di)

        unmatched_t = [i for i in range(len(tracks)) if i not in used_t]
        unmatched_d = [i for i in range(len(detections)) if i not in used_d]
        return matched, unmatched_t, unmatched_d

    # ------------------------------------------------------------------ #
    #  Unused abstract methods (tracking is stateful, driven by __call__) #
    # ------------------------------------------------------------------ #
    def preprocess(self, frame): return frame
    def inference(self, p): return {}
    def postprocess(self, r): return {}

    def unload(self):
        self.model = None
        self._tracks = []


# ─────────────────────────────────────────────────────────────────────────────
#  Utility
# ─────────────────────────────────────────────────────────────────────────────

def _iou_bbox(b1, b2) -> float:
    x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    a1 = max(0, b1[2] - b1[0]) * max(0, b1[3] - b1[1])
    a2 = max(0, b2[2] - b2[0]) * max(0, b2[3] - b2[1])
    return inter / (a1 + a2 - inter + 1e-8)
