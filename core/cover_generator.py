"""表紙関連生成モジュール"""
from core.claude_client import call_claude
from core.json_utils import extract_json
from config import PROMPTS_DIR


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def generate_cover_assets(candidate: dict, target: str) -> dict:
    """
    表紙用の素材一式を生成する。

    【トークン節約設計】
    タイトル・サブタイトル・バッジはcandidateにすでに確定済みのためPythonで流用。
    AIにはデザインコンセプト・配色・画像プロンプトだけを生成させる。

    返り値:
    {
        "title": "...",          # candidateから流用
        "subtitle": "...",       # candidateから流用
        "badges": ["...", ...],  # candidateから流用
        "color_scheme": "...",   # AIが生成
        "design_concept": "...", # AIが生成
        "image_prompt": "..."    # AIが生成
    }
    """
    system_prompt = load_prompt("generate_cover.md")
    user_prompt = f"""
# 確定済みタイトル
{candidate.get("title", "")}

# 確定済みサブタイトル
{candidate.get("subtitle", "")}

# 特典コンセプト
{candidate.get("concept", "")}

# ターゲット（詳細）
{target}

# ターゲットの悩み
{candidate.get("target_pain", "")}

# ターゲットの理想
{candidate.get("target_ideal", "")}

上記の情報をもとに、このターゲットと特典内容に合った
表紙デザインコンセプト・配色・AI画像プロンプトを設計してください。
"""
    raw = call_claude(system_prompt, user_prompt, max_tokens=1000)

    design = extract_json(raw, {"design_concept": raw, "color_scheme": "", "subject": "", "image_prompt": ""})

    # タイトル・サブタイトル・バッジはcandidateから流用（AI再生成不要）
    result = {
        "title":          candidate.get("title", ""),
        "subtitle":       candidate.get("subtitle", ""),
        "badges":         candidate.get("badges", []),
        "color_scheme":   design.get("color_scheme", ""),
        "subject":        design.get("subject", ""),
        "design_concept": design.get("design_concept", ""),
        "image_prompt":   design.get("image_prompt", ""),
    }
    return result
