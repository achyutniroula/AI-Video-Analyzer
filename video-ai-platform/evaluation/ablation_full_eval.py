"""
ablation_full_eval.py
---------------------
Comprehensive ablation evaluation across all variants for the same source videos.

Metrics computed:
  - ROUGE-L (lexical overlap vs ground truth)
  - BERTScore F1 (semantic similarity vs ground truth)
  - Claude evaluation (Factual Accuracy, Temporal Coherence, Detail Richness, Fluency)

Usage:
    python ablation_full_eval.py
    python ablation_full_eval.py --skip-bertscore   # faster
    python ablation_full_eval.py --out results.json
"""

import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

# ── Video mapping ─────────────────────────────────────────────────────────────
# Each entry: (video_id, variant_label, gt_video_id or None)
# gt_video_id: which GT entry to use for automated metrics

CITY_GT  = "4836f75d-7130-4962-92f5-4f0ec9b3b3bf"
FOREST_GT = "56ced09a-425a-4a1a-9ee7-2a62634ee024"

VARIANTS = [
    # ── City video ablation ──────────────────────────────────────────────────
    ("4836f75d-7130-4962-92f5-4f0ec9b3b3bf", "Full System",        "city",   CITY_GT),
    ("55418726-0241-40cb-a954-2af17a24ca73", "No Depth",           "city",   CITY_GT),
    ("5393290e-466a-4451-a6d3-6936b40797ae", "No Audio",           "city",   CITY_GT),
    ("d2cd5b12-aa45-4622-81f8-5475ac9cdf24", "No Action",           "city",   CITY_GT),
    ("5337693e-1961-46fc-87ee-d9190bc1731c", "VLM-only",           "city",   CITY_GT),
    ("db87a460-7a0e-468b-ab0f-7dd6aba7c735", "Phase 2 Baseline",   "city",   CITY_GT),
    # ── Forest video comparison ──────────────────────────────────────────────
    ("56ced09a-425a-4a1a-9ee7-2a62634ee024", "Full System",        "forest", FOREST_GT),
    ("1fe6730c-069a-4ace-9c55-a3a292a12e8a", "Full System (W/O Music)", "forest", FOREST_GT),
    ("68decf19-aeea-4a09-bcc7-3746666ef843", "Phase 2 Baseline",   "forest", FOREST_GT),
    # ── Phase 2 only (no GT for automated metrics) ───────────────────────────
    ("d5b011e3-b712-4062-8d50-21129b3fa0c4", "Phase 2 Baseline",   "indoors", None),
    ("56a31dac-1ff8-4865-bc2e-f14b962e83f1", "Phase 2 Baseline",   "hands",   None),
    ("f6690dba-a5ac-48a1-b288-2daaed471d2e", "Phase 2 Baseline",   "person",  None),
]

CLAUDE_EVAL_PROMPT = """\
You are evaluating a generated video narrative against a ground truth description.

Ground Truth:
{ground_truth}

Generated Narrative:
{narrative}

Score the generated narrative on each dimension (1–5 scale):
- Factual Accuracy: Does it correctly describe what actually happens in the video?
- Temporal Coherence: Does it flow logically through time?
- Detail Richness: Does it mention specific objects, actions, spatial relationships, audio?
- Fluency: Is it natural, readable, and well-written?

Respond ONLY with valid JSON in exactly this format:
{{
  "factual_accuracy": <1-5>,
  "temporal_coherence": <1-5>,
  "detail_richness": <1-5>,
  "fluency": <1-5>,
  "comment": "<one sentence summary of the narrative's main strength or weakness>"
}}"""

CLAUDE_EVAL_PROMPT_NO_GT = """\
You are evaluating a generated video narrative for quality.

Generated Narrative:
{narrative}

Score the narrative on each dimension (1–5 scale):
- Factual Accuracy: Does it read as a plausible, consistent description of a real video?
- Temporal Coherence: Does it flow logically through time?
- Detail Richness: Does it mention specific objects, actions, spatial relationships, audio?
- Fluency: Is it natural, readable, and well-written?

Respond ONLY with valid JSON in exactly this format:
{{
  "factual_accuracy": <1-5>,
  "temporal_coherence": <1-5>,
  "detail_richness": <1-5>,
  "fluency": <1-5>,
  "comment": "<one sentence summary of the narrative's main strength or weakness>"
}}"""


def get_narrative_text(entry: dict) -> str:
    narr = entry.get("narrative", "")
    if isinstance(narr, dict):
        return narr.get("narrative", "")
    return narr or ""


def compute_rouge_l(reference: str, hypothesis: str) -> float:
    from rouge_score import rouge_scorer
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    return round(scorer.score(reference, hypothesis)["rougeL"].fmeasure, 4)


def compute_bertscore(references: list, hypotheses: list) -> list:
    from bert_score import score as bert_score
    print("  Computing BERTScore...")
    _, _, F1 = bert_score(hypotheses, references, lang="en", verbose=False)
    return [round(v.item(), 4) for v in F1]


def claude_evaluate(narrative: str, ground_truth, api_key: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    if ground_truth:
        prompt = CLAUDE_EVAL_PROMPT.format(ground_truth=ground_truth, narrative=narrative[:3000])
    else:
        prompt = CLAUDE_EVAL_PROMPT_NO_GT.format(narrative=narrative[:3000])

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"    Claude eval error: {e}")
        return {"factual_accuracy": None, "temporal_coherence": None,
                "detail_richness": None, "fluency": None, "comment": f"error: {e}"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-bertscore", action="store_true")
    parser.add_argument("--skip-claude",    action="store_true")
    parser.add_argument("--out", default="results_ablation_full.json")
    args = parser.parse_args()

    # Load data
    with open("all_narratives.json", encoding="utf-8") as f:
        all_n = json.load(f)
    with open("ground_truth.json", encoding="utf-8") as f:
        gt_data = json.load(f)

    by_id    = {v["video_id"]: v for v in all_n["videos"]}
    gt_by_id = {v["video_id"]: v for v in gt_data["videos"]}

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.skip_claude:
        from dotenv import load_dotenv
        for candidate in [
            os.path.join(os.path.dirname(__file__), "..", "newworker", ".env"),
            os.path.join(os.path.dirname(__file__), ".env"),
        ]:
            if os.path.exists(candidate):
                load_dotenv(candidate)
                break
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # ── Build evaluation entries ──────────────────────────────────────────────
    entries = []
    for vid_id, variant, category, gt_vid_id in VARIANTS:
        if vid_id is None:
            entries.append({
                "video_id": None, "variant": variant, "category": category,
                "narrative": None, "gt_text": None, "missing": True,
            })
            continue

        db_entry = by_id.get(vid_id)
        if not db_entry:
            entries.append({
                "video_id": vid_id, "variant": variant, "category": category,
                "narrative": None, "gt_text": None, "missing": True,
            })
            continue

        narrative = get_narrative_text(db_entry)
        gt_entry  = gt_by_id.get(gt_vid_id) if gt_vid_id else None
        gt_text   = gt_entry.get("ground_truth", "").strip() if gt_entry else None

        entries.append({
            "video_id":  vid_id,
            "variant":   variant,
            "category":  category,
            "narrative": narrative,
            "gt_text":   gt_text,
            "missing":   not bool(narrative),
        })

    # ── ROUGE-L ───────────────────────────────────────────────────────────────
    print("\nComputing ROUGE-L...")
    for e in entries:
        if e["missing"] or not e["gt_text"]:
            e["rouge_l"] = None
        else:
            e["rouge_l"] = compute_rouge_l(e["gt_text"], e["narrative"])
            print(f"  {e['category']:<10} {e['variant']:<28} ROUGE-L={e['rouge_l']}")

    # ── BERTScore ─────────────────────────────────────────────────────────────
    if not args.skip_bertscore:
        scorable = [e for e in entries if not e["missing"] and e["gt_text"]]
        if scorable:
            scores = compute_bertscore(
                [e["gt_text"]   for e in scorable],
                [e["narrative"] for e in scorable],
            )
            for e, s in zip(scorable, scores):
                e["bertscore"] = s
        for e in entries:
            if "bertscore" not in e:
                e["bertscore"] = None
    else:
        for e in entries:
            e["bertscore"] = None

    # ── Claude evaluation ─────────────────────────────────────────────────────
    if not args.skip_claude and api_key:
        print("\nRunning Claude evaluation (haiku-4-5)...")
        for e in entries:
            if e["missing"]:
                e["claude"] = None
                continue
            print(f"  Evaluating: {e['category']}/{e['variant']}...")
            e["claude"] = claude_evaluate(e["narrative"], e["gt_text"], api_key)
            time.sleep(0.5)  # avoid rate limit
    else:
        for e in entries:
            e["claude"] = None

    # ── Print tables ──────────────────────────────────────────────────────────
    try:
        from tabulate import tabulate

        for cat in ["city", "forest", "indoors", "hands", "person"]:
            cat_entries = [e for e in entries if e["category"] == cat]
            if not cat_entries:
                continue

            print(f"\n{'='*90}")
            print(f"  {cat.upper()} VIDEO")
            print(f"{'='*90}")

            rows = []
            for e in cat_entries:
                if e["missing"]:
                    rows.append([e["variant"], "—", "—", "—", "—", "—", "—", "not processed"])
                    continue
                c = e.get("claude") or {}
                avg_claude = None
                if c and all(c.get(k) for k in ("factual_accuracy","temporal_coherence","detail_richness","fluency")):
                    avg_claude = round(sum([c["factual_accuracy"], c["temporal_coherence"],
                                           c["detail_richness"], c["fluency"]]) / 4, 2)
                rows.append([
                    e["variant"],
                    f"{e['rouge_l']:.4f}"   if e["rouge_l"]   is not None else "—",
                    f"{e['bertscore']:.4f}" if e["bertscore"] is not None else "—",
                    c.get("factual_accuracy")  or "—",
                    c.get("temporal_coherence") or "—",
                    c.get("detail_richness")   or "—",
                    c.get("fluency")           or "—",
                    f"{avg_claude}" if avg_claude else "—",
                ])

            headers = ["Variant", "ROUGE-L", "BERTScore", "Accuracy", "Coherence", "Detail", "Fluency", "Avg"]
            print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))

            # Comments
            print()
            for e in cat_entries:
                c = e.get("claude") or {}
                if c and c.get("comment"):
                    print(f"  [{e['variant']}] {c['comment']}")

    except ImportError:
        for e in entries:
            print(e)

    # ── Save ─────────────────────────────────────────────────────────────────
    with open(args.out, "w", encoding="utf-8") as f:
        safe = [{k: v for k, v in e.items() if k not in ("narrative", "gt_text")} for e in entries]
        json.dump(safe, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Results saved to '{args.out}'")


if __name__ == "__main__":
    main()
