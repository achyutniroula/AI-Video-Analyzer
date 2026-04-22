# Video AI Platform

An end-to-end video analysis platform that accepts user-uploaded videos, runs a multi-model AI perception pipeline on AWS GPU infrastructure, and returns a structured narrative with object detections, scene understanding, and timestamped summaries.

## Architecture

```
Upload (Next.js)
    → S3 (video storage)
    → SQS (event queue)
    → EC2 Worker (AI pipeline)
    → DynamoDB + S3 (results)
    → Dashboard (Next.js)
```

**Frontend** — Next.js, AWS Amplify, Cognito authentication  
**Backend** — FastAPI, Python, JWT validation, REST + WebSocket  
**Worker** — Multi-model GPU pipeline on EC2 (g4dn.xlarge)  
**Storage** — S3 (videos + detection JSON), DynamoDB (metadata + summaries)

## AI Pipeline (Worker)

The worker runs a sequential perception stack, fuses results, and generates a narrative.

**Perception**
- Mask2Former — panoptic segmentation (every pixel labeled)
- DepthAnything V2 — monocular depth estimation
- SigLIP — zero-shot scene classification
- Scene Graph - Spatial Relations
- ByteTrack - Multi-Object Tracking
- SlowFast R50 — action recognition (Kinetics-400)
- Whisper large-v3 (faster-whisper) — speech transcription
- CLAP (HTS-AT) — audio event classification (28 categories)
- Chromaprint + AcoustID — music fingerprinting

**Fusion**
- Siloed detections from all the models
- Scene graph generation from spatial bounding box relationships
- Unified scene representation combining all modalities

**Narrative**
- Qwen2-VL-7B-Instruct — per-frame visual captioning (8-bit quantized)
- Claude claude-sonnet-4-6 — temporal narrative generation with timestamps

## Setup

### Prerequisites

- Node.js 18+
- Python 3.11
- AWS account with IAM permissions for S3, SQS, DynamoDB, Cognito, ECR, EC2
- Docker (for worker deployment)
- FFmpeg (added to system PATH)

### AWS Resources

Create the following in `us-east-2` (or your preferred region):

1. **Cognito** — User Pool with email login; note the Pool ID and App Client ID
2. **S3 bucket** — for video uploads and result JSON
3. **SQS queue** — standard queue; configure S3 event notifications to publish to it
4. **DynamoDB table** — primary key `video_id`
5. **IAM user** — with `AmazonS3FullAccess`, `AmazonSQSFullAccess`, `AmazonDynamoDBFullAccess`
6. **ECR repository** — for the worker Docker image
7. **EC2 instance** — `g4dn.xlarge` with Deep Learning AMI GPU PyTorch, 100 GB gp3 storage

### Frontend

```bash
cd video-ai-frontend
npm install
```

Create `app/lib/aws-config.js` with your Cognito Pool ID and Client ID, then:

```bash
npm run dev
```

### Backend

```bash
cd video-ai-platform/backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Create `.env`:

```
AWS_REGION=us-east-2
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=your-bucket
SQS_QUEUE_URL=https://sqs.us-east-2.amazonaws.com/your-account-id/your-queue
DYNAMODB_TABLE_NAME=video-detections
ANTHROPIC_API_KEY=your_anthropic_key
```

```bash
uvicorn app.main:app --reload --port 8000
```

### Worker (EC2 Deployment)

**Build and push Docker image locally:**

```bash
cd video-ai-platform/newworker
docker build -t video-ai-worker:latest .
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-2.amazonaws.com
docker tag video-ai-worker:latest <account-id>.dkr.ecr.us-east-2.amazonaws.com/video-ai-worker:latest
docker push <account-id>.dkr.ecr.us-east-2.amazonaws.com/video-ai-worker:latest
```

**On EC2 (via SSH):**

```bash
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-2.amazonaws.com
docker pull <account-id>.dkr.ecr.us-east-2.amazonaws.com/video-ai-worker:latest
```

Create `worker.env` with the same variables as the backend `.env`, then:

```bash
docker run -d \
  --gpus all \
  --name video-worker \
  --env-file worker.env \
  --restart unless-stopped \
  <account-id>.dkr.ecr.us-east-2.amazonaws.com/video-ai-worker:latest
```

**Check logs:**

```bash
docker logs -f video-worker
```

### Worker (Direct EC2, no Docker)

```bash
python3 -m venv venv && source venv/bin/activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers==4.47.1
pip install -r requirements.txt
sudo apt-get install -y libchromaprint-tools
pip install faster-whisper pyacoustid
python tests/test_pipeline.py --gpu   # verify GPU pipeline
python main.py                        # start polling SQS
```

## Cost Management

The EC2 GPU instance is the primary cost driver. Stop it when not in use:

```
AWS Console → EC2 → Select instance → Instance state → Stop
```

On restart, the public IP changes. SSH in with the new IP and run `docker start video-worker`.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, AWS Amplify, Tailwind CSS |
| Auth | AWS Cognito |
| Backend API | FastAPI, Python 3.11 |
| Queue | AWS SQS |
| Storage | AWS S3, DynamoDB |
| Object Detection | YOLOv8, SAM2, Mask2Former |
| Scene Understanding | SigLIP, DepthAnything V2, SlowFast |
| Audio | Whisper large-v3, CLAP, Chromaprint |
| VLM Captioning | Qwen2-VL-7B-Instruct |
| Narrative | Claude claude-sonnet-4-6 (Anthropic) |
| Containerization | Docker, AWS ECR |
| Compute | AWS EC2 g4dn.xlarge (GPU) |
