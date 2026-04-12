import os
from pathlib import Path

# ローカル開発時: .env ファイルから読み込む
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---- パス ----
BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"
DATA_DIR = BASE_DIR / "data" / "projects"
OUTPUT_DIR = BASE_DIR / "output" / "projects"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _get(key: str, default: str = "") -> str:
    """
    環境変数を取得する。
    優先順位: os.environ > Streamlit Secrets（クラウドデプロイ時）
    """
    val = os.getenv(key, "")
    if val:
        return val
    # Streamlit Cloud のシークレットにフォールバック
    try:
        import streamlit as st
        return str(st.secrets.get(key, default))
    except Exception:
        return default


# ---- AIプロバイダー設定 ----
# PROVIDER: anthropic / openai / gemini
PROVIDER = _get("PROVIDER", "gemini").lower()

# Anthropic (Claude)
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = _get("CLAUDE_MODEL", "claude-sonnet-4-6")

# OpenAI (GPT)
OPENAI_API_KEY = _get("OPENAI_API_KEY", "")
OPENAI_MODEL = _get("OPENAI_MODEL", "gpt-4o")

# Google (Gemini) ← 無料枠あり・デフォルト
GEMINI_API_KEY = _get("GEMINI_API_KEY", "")
GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-2.5-flash")

# ---- 品質基準 ----
MIN_SECTION_CHARS = 2500
MIN_SECTIONS = 5
MAX_TITLE_CHARS = 32
MAX_SUBTITLE_CHARS = 60

# ---- ストーリー構造 ----
STORY_STRUCTURE = ["未来", "問題提起", "原因", "解決策", "ハウツー", "ティザー"]

# ---- レポート基本構成 ----
REPORT_SECTIONS = ["表紙", "あいさつ", "はじめに", "本文", "おわりに", "利用規約"]
