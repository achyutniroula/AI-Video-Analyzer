"""
ablation_summary.py
-------------------
Reads the per-variant results JSON files produced by evaluate.py --out
and prints a single comparison table across all ablation variants.

Usage:
    python ablation_summary.py
    python ablation_summary.py --results-dir .          # default: current dir
    python ablation_summary.py --out ablation_table.json
"""

import argparse
import json
import os
import sys


VARIANTS = [
    ("results_city2_full.json",     "Full System (baseline)"),
    ("results_no_depth.json",       "No Depth"),
    ("results_no_audio.json",       "No Audio"),
    ("results_no_action.json",      "No Action"),
    ("results_no_scene_graph.json", "No Scene Graph"),
    ("results_vlm_only.json",       "VLM-only (No Fusion)"),
]


def load_summary(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("summary", {})


def delta(value: float, baseline: float) -> str:
    if value is None or baseline is None:
        return ""
    diff = value - baseline
    sign = "+" if diff >= 0 else ""
    return f"({sign}{diff:+.4f})"


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Ablation study comparison table")
    parser.add_argument("--results-dir", default=".", help="Directory containing results_*.json files")
    parser.add_argument("--out", default=None, help="Save table data to this JSON file")
    args = parser.parse_args()

    rows = []
    baseline = None

    for filename, label in VARIANTS:
        path = os.path.join(args.results_dir, filename)
        summary = load_summary(path)
        if summary is None:
            rows.append({"label": label, "missing": True})
            continue
        rows.append({
            "label":      label,
            "n":          summary.get("videos_evaluated", "?"),
            "rouge_l":    summary.get("avg_rouge_l"),
            "bleu":       summary.get("avg_bleu"),
            "bertscore":  summary.get("avg_bertscore_f1"),
            "missing":    False,
        })
        if baseline is None and not rows[-1]["missing"]:
            baseline = rows[-1]

    # ── Print table ───────────────────────────────────────────────────────────
    try:
        from tabulate import tabulate

        headers = ["Variant", "N", "ROUGE-L", "Δ", "BLEU", "Δ", "BERTScore F1", "Δ"]
        table = []
        for r in rows:
            if r.get("missing"):
                table.append([r["label"], "—", "—", "", "—", "", "—", ""])
                continue
            b = baseline or {}
            table.append([
                r["label"],
                r["n"],
                f"{r['rouge_l']:.4f}"   if r["rouge_l"]   is not None else "—",
                delta(r["rouge_l"],  b.get("rouge_l"))   if r is not baseline else "",
                f"{r['bleu']:.4f}"      if r["bleu"]      is not None else "—",
                delta(r["bleu"],     b.get("bleu"))       if r is not baseline else "",
                f"{r['bertscore']:.4f}" if r["bertscore"] is not None else "skipped",
                delta(r["bertscore"], b.get("bertscore")) if r is not baseline else "",
            ])

        print("\nAblation Study Results")
        print("=" * 80)
        print(tabulate(table, headers=headers, tablefmt="rounded_outline"))

    except ImportError:
        print("\nAblation Study Results")
        print("=" * 80)
        print(f"{'Variant':<28} {'N':>3}  {'ROUGE-L':>8}  {'BLEU':>7}  {'BERTScore':>10}")
        print("-" * 65)
        for r in rows:
            if r.get("missing"):
                print(f"  {'[missing] ' + r['label']:<26} {'—':>3}  {'—':>8}  {'—':>7}  {'—':>10}")
                continue
            bs = f"{r['bertscore']:.4f}" if r["bertscore"] is not None else "skipped"
            print(f"  {r['label']:<26} {r['n']:>3}  {r['rouge_l']:.4f}    {r['bleu']:.4f}    {bs}")

    # ── Missing files notice ──────────────────────────────────────────────────
    missing = [r["label"] for r in rows if r.get("missing")]
    if missing:
        print(f"\n  Not yet run: {', '.join(missing)}")
        print("  Run evaluate.py --out results_<variant>.json for each missing variant.")

    # ── Save ─────────────────────────────────────────────────────────────────
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump([r for r in rows if not r.get("missing")], f, indent=2)
        print(f"\n✓ Table data saved to '{args.out}'")


if __name__ == "__main__":
    main()
