"""
SlowFast R50 Action Recognizer

Classifies human actions from a short video clip using the two-pathway
SlowFast architecture (slow: low frame rate, high spatial res;
fast: high frame rate, low spatial res).

Model: facebookresearch/pytorchvideo — slowfast_r50 (Kinetics-400 pretrained)
Input: clip of 32 frames (or single frame tiled for testing)
Output: top-5 actions with confidence scores
VRAM: ~3.5GB (FP32, can run FP16 manually)
Time: ~0.2s per clip on A10
"""

import time
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn.functional as F

from .base import BasePerceptionModule, PerceptionOutput

# Kinetics-400 label list (full 400 classes)
_K400_LABELS = [
    "abseiling","air drumming","answering questions","archery","arguing",
    "arm wrestling","arranging flowers","assembling computer","attending conference",
    "auctioning","baby waking up","baking cookies","balloon blowing","bandaging",
    "barbequing","bartending","beatboxing","bee keeping","belly dancing",
    "bench pressing","biking through snow","blasting sand","blowing glass",
    "blowing leaves","blowing nose","blowing out candles","bobsledding","bookbinding",
    "bouncing on trampoline","bowling","braiding hair","breading or breadcrumbing",
    "breakdancing","brush painting","brushing hair","brushing teeth",
    "building cabinet","building shed","bungee jumping","busking",
    "canoeing or kayaking","capoeira","carrying baby","cartwheeling",
    "carving pumpkin","catching fish","catching or throwing baseball",
    "catching or throwing frisbee","catching or throwing softball","celebrating",
    "changing oil","changing wheel","checking tires","cheerleading","chopping wood",
    "clapping","clay pottery making","clean and jerk","cleaning floor",
    "cleaning gutters","cleaning pool","cleaning shoes","cleaning toilet",
    "cleaning windows","climbing a rope","climbing ladder","climbing tree",
    "contact juggling","cooking chicken","cooking egg","cooking on campfire",
    "cooking sausages","counting money","country line dancing","cracking knuckles",
    "cracking neck","crawling baby","crossing river","crying","curling hair",
    "cutting nails","cutting pineapple","cutting watermelon","dancing ballet",
    "dancing charleston","dancing gangnam style","dancing macarena","deadlifting",
    "decorating the christmas tree","digging","dining","disc golfing",
    "diving cliff","dodgeball","doing aerobics","doing laundry","doing nails",
    "drawing","dribbling basketball","drinking","drinking beer","drinking shots",
    "driving car","driving tractor","drop kicking","drumming fingers",
    "dunking basketball","dying hair","eating burger","eating cake",
    "eating carrots","eating chips","eating doughnuts","eating hotdog",
    "eating ice cream","eating spaghetti","eating watermelon","egg hunting",
    "exercising arm","exercising with an exercise ball","extinguishing fire",
    "faceplanting","feeding birds","feeding fish","feeding goats",
    "filling eyebrows","finger snapping","fixing hair","flipping pancake",
    "fly tying","flying kite","folding clothes","folding napkins","folding paper",
    "front raises","frying vegetables","garbage collecting","gargling",
    "getting a haircut","getting a tattoo","giving or receiving award",
    "gold panning","golf chipping","golf driving","golf putting","grinding meat",
    "grooming dog","grooming horse","gymnastics tumbling","hammer throw",
    "headbanging","headbutting","high jump","high kick","hitting baseball",
    "hockey stop","holding snake","hopscotch","hoverboarding","hugging",
    "hula hooping","hurdling","hurling","ice climbing","ice fishing",
    "ice skating","ironing","javelin throw","jetskiing","jogging",
    "jumping into pool","jumping jacks","jumping sofa","kayaking",
    "kicking field goal","kicking soccer ball","kissing","kitesurfing",
    "knitting","krumping","laughing","laying bricks","long jump","lunge",
    "making a cake","making a sandwich","making bed","making jewelry",
    "making pizza","making snowman","making sushi","making tea","marching",
    "massaging back","massaging feet","massaging legs","massaging person's head",
    "milking cow","mopping floor","motorcycling","moving furniture","mowing lawn",
    "news anchoring","opening bottle","opening present","paragliding",
    "parasailing","parkour","passing American football (in game)",
    "passing American football (not in game)","peeling apples","peeling potatoes",
    "petting animal (not cat)","petting cat","picking fruit","planting trees",
    "plastering","playing accordion","playing badminton","playing bagpipes",
    "playing basketball","playing bass guitar","playing cards","playing cello",
    "playing checkers","playing chess","playing clarinet","playing controller",
    "playing cricket","playing cymbals","playing didgeridoo","playing drums",
    "playing flute","playing guitar","playing harmonica","playing harp",
    "playing ice hockey","playing keyboard","playing kickball","playing monopoly",
    "playing organ","playing paintball","playing piano","playing poker",
    "playing recorder","playing rugby","playing saxophone",
    "playing squash or racquetball","playing tennis","playing trombone",
    "playing trumpet","playing ukulele","playing violin","playing volleyball",
    "playing xylophone","pole vault","presenting weather forecast","pull ups",
    "pumping fist","pumping gas","push up","pushing car","pushing cart",
    "pushing wheelchair","reading book","reading newspaper","recording music",
    "riding a bike","riding camel","riding elephant","riding mechanical bull",
    "riding mountain bike","riding mule","riding or walking with horse",
    "riding scooter","riding segway","riding tractor","riding unicycle",
    "riding water scooter","rock climbing","rock scissors paper",
    "roller skating","running on treadmill","sailing","salsa dancing",
    "sanding floor","scrambling eggs","scuba diving","setting table",
    "shaking hands","shaking head","sharpening knives","sharpening pencil",
    "shaving head","shaving legs","shearing sheep","shining shoes",
    "shooting basketball","shooting goal (soccer)","shot put","shoveling snow",
    "shredding paper","shuffling cards","side kick","sign language interpreting",
    "singing","situp","skateboarding","ski jumping",
    "skiing (not slalom or cross country)","skiing slalom","skipping rope",
    "skydiving","slacklining","slapping","sled dog racing","smoking",
    "smoking hookah","snatch weight lifting","sneezing","sniffing","snorkeling",
    "snowboarding","snowkiting","snowmobiling","somersaulting","spinning poi",
    "spray painting","springboard diving","squat","sticking tongue out",
    "stretching arm","stretching leg","strumming guitar","surfing crowd",
    "surfing water","sweeping floor","swimming backstroke",
    "swimming breast stroke","swimming butterfly stroke","swing dancing",
    "swinging legs","swinging on something","sword fighting","tai chi",
    "taking a shower","tango dancing","tap dancing","tapping guitar",
    "tapping pen","tasting beer","tasting food","testifying","texting",
    "throwing axe","throwing ball","throwing discus","tickling","tobogganing",
    "tossing coin","tossing salad","training dog","trapezing",
    "trimming or shaving beard","trimming trees","triple jump",
    "twiddling fingers","tying bow tie","tying knot (not on a tie)","tying tie",
    "unboxing","unloading truck","using computer",
    "using remote controller (not gaming)","using segway","vault",
    "waiting in line","walking the dog","washing dishes","washing feet",
    "washing hair","washing hands","water skiing","water sliding",
    "watering plants","waxing back","waxing chest","waxing eyebrows",
    "waxing legs","weaving basket","welding","whistling","windsurfing",
    "wrapping present","wrestling","writing","yawning","yoga","zumba",
]


class ActionRecognizer(BasePerceptionModule):
    """
    SlowFast R50 action recognizer.

    Requires a clip (list of frames or (T,H,W,3) array) passed via the
    `clip` kwarg.  When no clip is given, the single frame is tiled to
    produce a synthetic clip — useful for testing but not for production.

    Example:
        rec = ActionRecognizer(device="cuda")
        rec.load_model()
        output = rec(frame, frame_id=5, timestamp=2.0, clip=frames_buffer)
        top = output.data["top_action"]   # {"action": "jogging", "confidence": 0.87}
        rec.unload()
    """

    NUM_FRAMES = 32    # fast-pathway frame count
    ALPHA = 4          # slow/fast ratio  → slow gets NUM_FRAMES // ALPHA frames
    CROP_SIZE = 224

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def load_model(self):
        print("Loading SlowFast R50 via torch.hub (facebookresearch/pytorchvideo)...")
        self.model = torch.hub.load(
            "facebookresearch/pytorchvideo",
            "slowfast_r50",
            pretrained=True,
            verbose=False,
        )
        self.model = self.model.to(self.device)
        self.model.eval()
        print(f"✓ SlowFast R50 loaded on {self.device}")

    # ------------------------------------------------------------------ #
    #  Override __call__ to accept an optional clip kwarg                  #
    # ------------------------------------------------------------------ #

    def __call__(
        self,
        frame: Any,
        frame_id: int,
        timestamp: float,
        clip: Optional[Any] = None,
        **kwargs,
    ) -> PerceptionOutput:
        t0 = time.time()
        if self.device == "cuda":
            torch.cuda.reset_peak_memory_stats()

        preprocessed = self.preprocess(frame, clip=clip)
        raw = self.inference(preprocessed)
        data = self.postprocess(raw)

        gpu_mem = None
        if self.device == "cuda":
            gpu_mem = torch.cuda.max_memory_allocated() / 1e9

        return PerceptionOutput(
            module_name=self.name,
            timestamp=timestamp,
            frame_id=frame_id,
            data=data,
            metadata={
                "device": self.device,
                "quantized": self.quantize,
                "clip_length": len(clip) if clip is not None else 1,
            },
            processing_time=time.time() - t0,
            gpu_memory_used=gpu_mem,
        )

    # ------------------------------------------------------------------ #
    #  BasePerceptionModule pipeline methods                               #
    # ------------------------------------------------------------------ #

    def preprocess(self, frame: Any, clip: Optional[Any] = None) -> List[torch.Tensor]:
        """Build [slow_pathway, fast_pathway] from clip or single frame."""
        # --- assemble raw frames array (T, H, W, 3) uint8 ---------------
        if clip is None:
            frames_np = np.stack(
                [frame.cpu().numpy() if isinstance(frame, torch.Tensor) else frame]
                * self.NUM_FRAMES
            )
        elif isinstance(clip, list):
            frames_np = np.stack(
                [f.cpu().numpy() if isinstance(f, torch.Tensor) else f for f in clip]
            )
        else:
            frames_np = clip.cpu().numpy() if isinstance(clip, torch.Tensor) else clip

        # --- temporal resampling to exactly NUM_FRAMES -------------------
        T = frames_np.shape[0]
        if T != self.NUM_FRAMES:
            idx = np.linspace(0, T - 1, self.NUM_FRAMES, dtype=int)
            frames_np = frames_np[idx]

        # --- normalise & convert to (1, 3, T, H, W) float tensor --------
        frames_f = frames_np.astype(np.float32) / 255.0
        mean = np.array([0.45, 0.45, 0.45], dtype=np.float32)
        std  = np.array([0.225, 0.225, 0.225], dtype=np.float32)
        frames_f = (frames_f - mean) / std

        # (T, H, W, 3) → (3, T, H, W) → (1, 3, T, H, W)
        t = torch.from_numpy(frames_f).permute(3, 0, 1, 2).unsqueeze(0)  # (1,3,T,H,W)

        # --- spatial resize to CROP_SIZE × CROP_SIZE --------------------
        b, c, tf, h, w = t.shape
        flat = t.reshape(b * tf, c, h, w)
        flat = F.interpolate(flat, size=(self.CROP_SIZE, self.CROP_SIZE),
                             mode="bilinear", align_corners=False)
        t = flat.reshape(b, c, tf, self.CROP_SIZE, self.CROP_SIZE)

        # --- build slow / fast pathways ----------------------------------
        fast = t.to(self.device)
        slow_idx = torch.linspace(0, tf - 1, tf // self.ALPHA).long()
        slow = t[:, :, slow_idx, :, :].to(self.device)

        return [slow, fast]

    def inference(self, preprocessed: List[torch.Tensor]) -> Dict[str, Any]:
        with torch.no_grad():
            logits = self.model(preprocessed)
        return {"logits": logits}

    def postprocess(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        logits = raw_output["logits"]
        probs = torch.softmax(logits, dim=-1)[0]
        top5_probs, top5_idx = torch.topk(probs, min(5, probs.shape[-1]))

        actions = []
        for prob, idx in zip(top5_probs.cpu().numpy(), top5_idx.cpu().numpy()):
            label = (
                _K400_LABELS[idx]
                if idx < len(_K400_LABELS)
                else f"action_{idx}"
            )
            actions.append(
                {"action": label, "confidence": round(float(prob), 4), "class_id": int(idx)}
            )

        return {
            "actions": actions,
            "top_action": actions[0] if actions else None,
        }
