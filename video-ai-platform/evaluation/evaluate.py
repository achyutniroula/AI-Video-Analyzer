"""
evaluate.py
-----------
Approach A: Automated Text Metrics for narrative quality evaluation.

Computes ROUGE-L, BLEU, and BERTScore between your system's generated
narratives and your manually-written ground truth descriptions.

Requires:
    pip install rouge-score nltk bert-score tabulate

On first run, BERTScore will download a ~500 MB BERT model (one time only).

Usage:
    python evaluate.py
    python evaluate.py --ground-truth ground_truth.json --narratives generated_narratives.json
    python evaluate.py --skip-bertscore          # fast mode, skips BERT download
    python evaluate.py --out results.json        # save detailed results
"""

import json
import argparse
import sys
import os


# ── Lazy imports with friendly install hints ──────────────────────────────────

def require(package, install_name=None):
    try:
        return __import__(package)
    except ImportError:
        name = install_name or package
        print(f"Missing package '{name}'. Install it with:  pip install {name}")
        sys.exit(1)


# ── Metric helpers ────────────────────────────────────────────────────────────

def compute_rouge_l(reference: str, hypothesis: str) -> float:
    from rouge_score import rouge_scorer
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = scorer.score(reference, hypothesis)
    return round(scores["rougeL"].fmeasure, 4)


def compute_bleu(reference: str, hypothesis: str) -> float:
    import nltk
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    # Download tokenizer data silently on first run
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)

    ref_tokens  = [reference.split()]
    hyp_tokens  = hypothesis.split()
    score = sentence_bleu(
        ref_tokens,
        hyp_tokens,
        smoothing_function=SmoothingFunction().method1
    )
    return round(score, 4)


def compute_bertscore(references: list[str], hypotheses: list[str]) -> list[float]:
    from bert_score import score as bert_score
    print("  Computing BERTScore (first run downloads ~500 MB BERT model)...")
    _, _, F1 = bert_score(hypotheses, references, lang="en", verbose=False)
    return [round(v.item(), 4) for v in F1]


# ── Main ──────────────────────────────────────────────────────────────────────

def load_json(path: str, label: str) -> dict:
    if not os.path.exists(path):
        print(f"File not found: {path}  ({label})")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Approach A: Automated narrative quality metrics")
    parser.add_argument("--ground-truth",    default="ground_truth.json",       help="Ground truth JSON file")
    parser.add_argument("--narratives",      default="generated_narratives.json", help="Generated narratives JSON file")
    parser.add_argument("--skip-bertscore",  action="store_true",               help="Skip BERTScore (faster, no download)")
    parser.add_argument("--out",             default=None,                      help="Save detailed results to this JSON file")
    args = parser.parse_args()

    # ── Load data ─────────────────────────────────────────────────────────────
    gt_data   = load_json(args.ground_truth, "ground_truth")
    gen_data  = load_json(args.narratives,   "generated_narratives")

    gt_map  = {v["video_id"]: v for v in gt_data.get("videos", [])}
    gen_map = {v["video_id"]: v for v in gen_data.get("videos", [])}

    # Find pairs that have both ground truth and a non-empty generated narrative
    matched = []
    skipped = []
    for vid_id, gt_entry in gt_map.items():
        gt_text = gt_entry.get("ground_truth", "").strip()
        if not gt_text or vid_id.startswith("REPLACE_WITH"):
            skipped.append((vid_id, "placeholder ground truth"))
            continue
        gen_entry = gen_map.get(vid_id)
        if not gen_entry:
            skipped.append((vid_id, "not found in generated_narratives.json"))
            continue
        gen_text = gen_entry.get("narrative", "").strip()
        if not gen_text:
            skipped.append((vid_id, "no narrative generated yet"))
            continue
        matched.append({
            "video_id":     vid_id,
            "title":        gt_entry.get("title", vid_id),
            "category":     gt_entry.get("category", ""),
            "reference":    gt_text,
            "hypothesis":   gen_text,
        })

    if skipped:
        print(f"\nSkipped {len(skipped)} video(s):")
        for vid_id, reason in skipped:
            print(f"  ✗ {vid_id[:36]}  — {reason}")

    if not matched:
        print("\nNo matched video pairs found. Make sure:")
        print("  1. ground_truth.json has real video_ids (not placeholders)")
        print("  2. generated_narratives.json has been populated by fetch_narratives.py")
        print("  3. The video_id values match exactly between the two files")
        sys.exit(1)

    print(f"\nEvaluating {len(matched)} video(s)...\n")

    # ── Compute per-video metrics ─────────────────────────────────────────────
    for entry in matched:
        entry["rouge_l"] = compute_rouge_l(entry["reference"], entry["hypothesis"])
        entry["bleu"]    = compute_bleu(entry["reference"],    entry["hypothesis"])

    if not args.skip_bertscore:
        bert_scores = compute_bertscore(
            [e["reference"]  for e in matched],
            [e["hypothesis"] for e in matched],
        )
        for entry, bs in zip(matched, bert_scores):
            entry["bertscore_f1"] = bs
    else:
        for entry in matched:
            entry["bertscore_f1"] = None

    # ── Summary table ─────────────────────────────────────────────────────────
    try:
        from tabulate import tabulate
        headers = ["Video", "Category", "ROUGE-L", "BLEU", "BERTScore F1"]
        rows = []
        for e in matched:
            rows.append([
                e["title"][:38],
                e["category"],
                f"{e['rouge_l']:.4f}",
                f"{e['bleu']:.4f}",
                f"{e['bertscore_f1']:.4f}" if e["bertscore_f1"] is not None else "skipped",
            ])
        print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    except ImportError:
        print("(Install 'tabulate' for a prettier table: pip install tabulate)\n")
        for e in matched:
            print(f"  {e['title'][:40]:<40}  ROUGE-L={e['rouge_l']:.4f}  BLEU={e['bleu']:.4f}  BERTScore={e.get('bertscore_f1', 'skipped')}")

    # ── Averages ──────────────────────────────────────────────────────────────
    avg_rouge = sum(e["rouge_l"] for e in matched) / len(matched)
    avg_bleu  = sum(e["bleu"]    for e in matched) / len(matched)
    print(f"\n  Average ROUGE-L  : {avg_rouge:.4f}")
    print(f"  Average BLEU     : {avg_bleu:.4f}")
    if not args.skip_bertscore:
        avg_bert = sum(e["bertscore_f1"] for e in matched) / len(matched)
        print(f"  Average BERTScore: {avg_bert:.4f}")

    print(f"\n  Videos evaluated : {len(matched)}")
    print(f"  Videos skipped   : {len(skipped)}")

    # ── Save detailed results ─────────────────────────────────────────────────
    if args.out:
        output = {
            "summary": {
                "videos_evaluated": len(matched),
                "avg_rouge_l":      round(avg_rouge, 4),
                "avg_bleu":         round(avg_bleu, 4),
                "avg_bertscore_f1": round(avg_bert, 4) if not args.skip_bertscore else None,
            },
            "per_video": [
                {k: v for k, v in e.items() if k not in ("reference", "hypothesis")}
                for e in matched
            ],
            "per_video_full": matched,
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Detailed results saved to '{args.out}'")


if __name__ == "__main__":
    main()
