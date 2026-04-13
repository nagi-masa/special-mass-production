"""素材分析モジュール：テーマ・悩み・理想・解決策を抽出する"""
from pathlib import Path
from core.claude_client import call_claude
from core.json_utils import extract_json
from config import PROMPTS_DIR


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def analyze_materials(
    materials: list[str],
    product_name: str,
    target: str,
    notes: str = "",
) -> dict:
    """
    複数素材を受け取り、以下を返す:
    {
        "themes": [...],
        "pain_points": [...],
        "ideal_outcomes": [...],
        "causes": [...],
        "solutions": [...],
        "teaser_elements": [...],
        "raw_summary": "..."
    }
    """
    from core.material_preprocessor import preprocess_materials, get_stats
    processed = preprocess_materials(materials)
    stats = get_stats(materials, processed)
    if stats["reduction_pct"] > 0:
        print(f"[前処理] {stats['original_chars']}文字 → {stats['processed_chars']}文字 ({stats['reduction_pct']}%削減)")
    combined = "\n\n---\n\n".join(processed)
    system_prompt = load_prompt("analyze_material.md")
    user_prompt = f"""
# 商品名
{product_name}

# ターゲット
{target}

# 補足メモ
{notes if notes else "なし"}

# 素材テキスト
{combined}
"""
    raw = call_claude(system_prompt, user_prompt, max_tokens=12000, json_mode=True)

    fallback = {
        "themes": [], "pain_points": [], "ideal_outcomes": [],
        "causes": [], "solutions": [], "teaser_elements": [],
    }
    result = extract_json(raw, fallback)
    result["raw_summary"] = raw
    return result
