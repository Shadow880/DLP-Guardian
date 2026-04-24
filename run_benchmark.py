import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from engine.policy_engine import decide_on_text
from test_prompts import test_prompts

# ── Config ──────────────────────────────────────────
TEST_USER = "employee1"   # employee role — strictest, fairest baseline
RESULTS_PATH = ROOT_DIR / "logs" / "benchmark_results.json"

# ── Run ─────────────────────────────────────────────
results = []
for item in test_prompts:
    decision = decide_on_text(item["text"], user=TEST_USER, source="benchmark")
    actual = decision.get("action", "allow")
    expected = item["expected"]
    correct = actual == expected
    results.append({
        "text": item["text"],
        "expected": expected,
        "actual": actual,
        "correct": correct,
        "risk_score": decision.get("risk_score", 0),
        "pattern_score": decision.get("pattern_score", 0),
        "semantic_score": round(float(decision.get("semantic_score", 0)), 3),
        "context_score": decision.get("context_score", 0),
        "fuzzy_score": decision.get("fuzzy_score", 0),
    })

# ── Compute metrics ──────────────────────────────────
total = len(results)
correct_count = sum(1 for r in results if r["correct"])
overall_accuracy = round(correct_count / total * 100, 1)

categories = ["allow", "warn", "block"]
print("\n" + "="*60)
print(f"OVERALL ACCURACY: {correct_count}/{total} = {overall_accuracy}%")
print("="*60)

for cat in categories:
    cat_items = [r for r in results if r["expected"] == cat]
    correct_in_cat = sum(1 for r in cat_items if r["correct"])
    if cat_items:
        pct = round(correct_in_cat / len(cat_items) * 100, 1)
        print(f"  {cat.upper():8s}: {correct_in_cat}/{len(cat_items)} correct = {pct}%")

# ── False positive / negative rates ─────────────────
# False positive = safe prompt incorrectly flagged (allow → warn/block)
safe_prompts = [r for r in results if r["expected"] == "allow"]
false_positives = [r for r in safe_prompts if r["actual"] != "allow"]
fp_rate = round(len(false_positives) / len(safe_prompts) * 100, 1)

# False negative = sensitive prompt incorrectly allowed (block/warn → allow)
sensitive_prompts = [r for r in results if r["expected"] in ["warn", "block"]]
false_negatives = [r for r in sensitive_prompts if r["actual"] == "allow"]
fn_rate = round(len(false_negatives) / len(sensitive_prompts) * 100, 1)

print(f"\n  FALSE POSITIVE RATE : {fp_rate}%  ({len(false_positives)} safe prompts incorrectly flagged)")
print(f"  FALSE NEGATIVE RATE : {fn_rate}%  ({len(false_negatives)} sensitive prompts missed)")

# ── Wrong predictions detail ─────────────────────────
wrong = [r for r in results if not r["correct"]]
if wrong:
    print(f"\n  INCORRECT PREDICTIONS ({len(wrong)}):")
    for r in wrong:
        print(f"    [{r['expected']} → {r['actual']}] risk={r['risk_score']} | {r['text'][:70]}")

# ── Save full results ────────────────────────────────
RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(RESULTS_PATH, "w") as f:
    json.dump({
        "overall_accuracy": overall_accuracy,
        "false_positive_rate": fp_rate,
        "false_negative_rate": fn_rate,
        "total": total,
        "correct": correct_count,
        "results": results
    }, f, indent=2)

print(f"\nFull results saved to {RESULTS_PATH}")
print("="*60)