# Narrative Quality Evaluation — Approach A Guide

This guide walks you through running **Approach A: Automated Text Metrics** (Step 2 of your paper experiments). By the end you will have three numeric scores — ROUGE-L, BLEU, and BERTScore — for each of your test videos, plus averages to put in your results table.

---

## What You Are Actually Doing

Your newworker generates a narrative (a 200–400 word description of what happens in a video). You write your own short description of the same video. These two texts are then compared using three standard NLP metrics.

Each metric measures something slightly different:

| Metric | What it measures | Range | Notes |
|--------|-----------------|-------|-------|
| **ROUGE-L** | Longest common subsequence of words | 0–1 | Penalizes paraphrasing. Fast and simple. |
| **BLEU** | N-gram overlap (how many word groups match) | 0–1 | Originally for machine translation. Widely cited. |
| **BERTScore F1** | Semantic similarity using BERT embeddings | ~0.8–1.0 for English | **Best metric for your case.** Does not penalize paraphrasing — "car" and "vehicle" both score well. |

All three together give reviewers confidence that your evaluation is thorough. A typical good system might score ROUGE-L ≈ 0.20–0.40, BLEU ≈ 0.05–0.20, BERTScore ≈ 0.85–0.92.

---

## File Overview

```
evaluation/
├── ground_truth.json          ← YOU fill this in (your human-written descriptions)
├── generated_narratives.json  ← Auto-populated by fetch_narratives.py
├── fetch_narratives.py        ← Pulls narratives from your DynamoDB table
├── evaluate.py                ← Runs all three metrics, prints results table
└── EVALUATION_GUIDE.md        ← This file
```

---

## Step-by-Step Instructions

### Step 0 — Install dependencies

Open a terminal in this folder and run:

```bash
pip install rouge-score nltk bert-score tabulate boto3
```

> **Note:** `bert-score` will download a ~500 MB BERT model the first time you run `evaluate.py`. This is a one-time download cached on your machine.

---

### Step 1 — Collect your test videos

Following the test plan in `Tests.docx`, collect **15–20 videos** across the six categories (outdoor, indoor, sports, speech-heavy, music performance, urban/street). Use Pixabay or Pexels for royalty-free downloads. Keep each video 15–60 seconds long.

Upload each video through your platform's upload page as normal. Wait for processing to complete (status = `completed`).

---

### Step 2 — Write your ground truth descriptions

**Do this before you look at what your system generated.** If you read the generated narrative first, your ground truth will be biased toward it.

Watch each video and write **2–4 sentences** covering:
- What is happening (actions/events)
- Who or what is present (people, objects, animals)
- The setting (indoor/outdoor, location)
- Any notable audio (speech, music, ambient noise)

Open `ground_truth.json` and fill in each entry. Example:

```json
{
  "videos": [
    {
      "video_id": "abc123-def456-...",
      "title": "Hiking trail at sunrise",
      "category": "outdoor",
      "source": "Pixabay",
      "duration_seconds": 30,
      "ground_truth": "A hiker walks along a narrow mountain trail at sunrise. The golden morning light illuminates rocky terrain and pine trees on either side. The hiker carries a red backpack and moves steadily uphill. Background sounds include birds chirping and wind through the trees."
    }
  ]
}
```

The `video_id` must match exactly what is in DynamoDB. Run the next step first if you need to look up your video IDs.

---

### Step 3 — Fetch generated narratives from DynamoDB

Make sure your AWS credentials are configured (they should already be, since your EC2 worker uses them). Then run:

```bash
python fetch_narratives.py
```

This scans your `video-detections` DynamoDB table and writes every completed video's narrative to `generated_narratives.json`. It also prints a list of all video IDs so you can copy them into `ground_truth.json`.

**Optional flags:**

```bash
# Filter to your specific Cognito user ID (get it from the Cognito console or the JWT payload)
python fetch_narratives.py --user-id YOUR_COGNITO_SUB

# Use a different AWS region or table name
python fetch_narratives.py --region us-east-1 --table video-detections

# Save to a different file
python fetch_narratives.py --out my_narratives.json
```

After this step you will have a file like:

```json
{
  "fetched_at": "2026-04-19T12:00:00Z",
  "videos": [
    {
      "video_id": "abc123-def456-...",
      "display_name": "Hiking trail",
      "status": "completed",
      "narrative": "The video opens on a sun-drenched mountain trail...",
      "has_narrative": true
    }
  ]
}
```

---

### Step 4 — Match video IDs between the two files

The evaluator matches videos by `video_id`. Make sure the `video_id` values in `ground_truth.json` are copy-pasted exactly from the output of `fetch_narratives.py`. They are UUID strings like `3f8a1c2d-...`.

---

### Step 5 — Run the evaluation

```bash
python evaluate.py
```

You will see output like:

```
Evaluating 16 video(s)...

  Computing BERTScore (first run downloads ~500 MB BERT model)...

╭──────────────────────────────────────┬──────────────┬─────────┬────────┬──────────────╮
│ Video                                │ Category     │ ROUGE-L │ BLEU   │ BERTScore F1 │
├──────────────────────────────────────┼──────────────┼─────────┼────────┼──────────────┤
│ Hiking trail at sunrise              │ outdoor      │ 0.2841  │ 0.0923 │ 0.8761       │
│ Person cooking pasta                 │ indoor       │ 0.3102  │ 0.1140 │ 0.8834       │
│ ...                                  │ ...          │ ...     │ ...    │ ...          │
╰──────────────────────────────────────┴──────────────┴─────────┴────────┴──────────────╯

  Average ROUGE-L  : 0.2950
  Average BLEU     : 0.1020
  Average BERTScore: 0.8803

  Videos evaluated : 16
  Videos skipped   : 0
```

To also save detailed per-video results to a JSON file:

```bash
python evaluate.py --out results.json
```

To skip BERTScore (faster, no download required — good for quick checks):

```bash
python evaluate.py --skip-bertscore
```

---

## Reading the Results

**ROUGE-L and BLEU are lower-bound metrics.** Your narrative is longer and richer than your 2–4 sentence ground truth, so these will naturally be on the lower side (~0.15–0.35). That is expected and normal — mention it in the paper.

**BERTScore is the most meaningful number.** It captures semantic similarity, so even if your system says "the vehicle accelerates" and your ground truth says "the car speeds up", BERTScore will correctly recognise these as equivalent. Scores above 0.85 indicate strong semantic overlap.

**What to put in your paper table:**

| System | ROUGE-L | BLEU | BERTScore F1 |
|--------|---------|------|--------------|
| Our system (Full Pipeline) | X.XXX | X.XXX | X.XXX |
| VLM-only baseline | X.XXX | X.XXX | X.XXX |
| YOLO-only (Phase 1/2) | X.XXX | X.XXX | X.XXX |

Run the same `evaluate.py` script for each baseline by simply replacing `generated_narratives.json` with the baseline's output (or use `--narratives baseline_vlm.json`).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No matched video pairs found` | Check that `video_id` in `ground_truth.json` exactly matches the IDs printed by `fetch_narratives.py` |
| `has_narrative: false` in generated_narratives | Video may still be processing, or the worker failed to generate a narrative. Check the system logs page in your frontend. |
| BERTScore download stuck | First run downloads `~500 MB`. Wait for it. Subsequent runs are instant. |
| `boto3.exceptions.NoCredentialsError` | Run `aws configure` or set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` environment variables. |
| AWS credentials work on EC2 but not locally | Your EC2 instance uses an IAM role. On your local machine, use the same IAM user credentials you use for the AWS console. |

---

## What Gets Measured — Plain English Summary

You built a video analysis system that combines 9 perception models (YOLO, Depth Anything, SlowFast, Whisper, CLAP, Chromaprint, SigLIP, a scene graph model, and Qwen2-VL) into a narrative description. Approach A answers the question: **"How accurate and semantically correct are those narratives?"**

You are the ground truth. You watch the video and write what you see in plain sentences. Your system watches the same video and generates its own narrative. The three metrics then measure how well the two descriptions agree — not word-for-word (that would be unfair, since your system writes more detail), but in terms of shared content, word patterns, and meaning.

This is a standard evaluation methodology used in academic papers on video captioning, dense video description, and multimodal AI systems.
