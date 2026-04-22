# Load from .env using dotenv
from dotenv import load_dotenv
load_dotenv()

import os


class Settings:
    AWS_REGION             = os.environ.get("AWS_REGION", "us-east-2")
    AWS_ACCESS_KEY_ID      = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY  = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    S3_BUCKET_NAME         = os.environ.get("S3_BUCKET_NAME", "")
    SQS_QUEUE_URL          = os.environ.get("SQS_QUEUE_URL", "")
    DYNAMODB_TABLE_NAME    = os.environ.get("DYNAMODB_TABLE_NAME", "video-detections")
    TEMP_DIR               = os.environ.get("TEMP_DIR", "./temp")
    SAMPLE_FPS             = float(os.environ.get("SAMPLE_FPS", "1.0"))
    DEVICE                 = os.environ.get("DEVICE", "cuda")
    QUANTIZE_BITS          = int(os.environ.get("QUANTIZE_BITS", "8"))

    _raw_disabled = os.environ.get("DISABLED_MODULES", "")
    DISABLED_MODULES: frozenset = frozenset(
        m.strip().lower() for m in _raw_disabled.split(",") if m.strip()
    )
    # Valid values: siglip, depth, panoptic, scene_graph, action, tracker,
    #               audio, fusion, vlm
    # "fusion" disables all perception modules + fusion (VLM-only mode).


settings = Settings()
