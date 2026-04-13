"""目次生成モジュール"""
from core.claude_client import call_claude
from core.json_utils import extract_json
from config import PROMPTS_DIR, MIN_SECTIONS, STORY_STRUCTURE


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def generate_toc(
    candidate: dict,
    analysis: dict,
    target: str,
) -> dict:
    """
    選ばれた特典候補1件の目次を生成する。
    返り値:
    {
        "sections": [
            {"number": 1, "title": "...", "role": "未来", "summary": "..."},
            ...
        ],
        "flow_check": "OK / NG: 理由..."
    }
    """
    system_prompt = load_prompt("generate_toc.md")
    user_prompt = f"""
# 特典タイトル
{candidate.get("title", "")}

# サブタイトル
{candidate.get("subtitle", "")}

# コンセプト
{candidate.get("concept", "")}

# ターゲット
{target}

# ターゲットの悩み
{candidate.get("target_pain", "")}

# ターゲットの理想
{candidate.get("target_ideal", "")}

# 素材から抽出した解決策
{analysis.get("solutions", [])}

# ストーリー構造（この順番で章を構成すること）
{" → ".join(STORY_STRUCTURE)}

# 最低セクション数
{MIN_SECTIONS}
"""
    raw = call_claude(system_prompt, user_prompt, max_tokens=4000)

    return extract_json(raw, {"sections": [], "flow_check": "解析失敗"})


def check_toc_validity(toc: dict) -> list[str]:
    """目次の品質問題をリストで返す（空なら問題なし）"""
    issues = []
    sections = toc.get("sections", [])

    if len(sections) < MIN_SECTIONS:
        issues.append(f"セクション数が{MIN_SECTIONS}未満です（現在: {len(sections)}）")

    roles = [s.get("role", "") for s in sections]
    seen = set()
    for role in roles:
        if role in seen:
            issues.append(f"ストーリー構造の役割が重複しています: {role}")
        seen.add(role)

    return issues
