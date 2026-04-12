"""特典候補生成モジュール"""
from core.claude_client import call_claude
from core.json_utils import extract_json
from config import PROMPTS_DIR


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def generate_candidates(
    analysis: dict,
    product_name: str,
    target: str,
) -> dict:
    """
    分析結果から特典候補を生成する。
    返り値:
    {
        "can_multiply": true/false,
        "reason": "...",
        "candidates": [
            {
                "id": 1,
                "title": "...",
                "subtitle": "...",
                "badges": ["...", "..."],
                "concept": "...",
                "target_pain": "...",
                "target_ideal": "..."
            },
            ...
        ]
    }
    """
    system_prompt = load_prompt("generate_candidates.md")
    user_prompt = f"""
# 商品名
{product_name}

# ターゲット
{target}

# 分析結果
テーマ: {analysis.get("themes", [])}
悩み: {analysis.get("pain_points", [])}
理想の未来: {analysis.get("ideal_outcomes", [])}
原因: {analysis.get("causes", [])}
解決策: {analysis.get("solutions", [])}
ティザー要素: {analysis.get("teaser_elements", [])}
"""
    raw = call_claude(system_prompt, user_prompt, max_tokens=4000)

    return extract_json(raw, {"can_multiply": False, "reason": "解析失敗", "candidates": []})
