"""AI クライアント共通モジュール（Anthropic / OpenAI / Gemini 対応）"""
import os
from config import PROVIDER, CLAUDE_MODEL, OPENAI_MODEL, GEMINI_MODEL


def _get_api_key(env_key: str) -> str:
    """APIキーを動的に取得（os.environ → Streamlit session_state → st.secrets の順）"""
    # まず os.environ から（app.py がセッションごとに上書きする）
    val = os.getenv(env_key, "")
    if val:
        return val
    # Streamlit Secrets にフォールバック
    try:
        import streamlit as st
        return str(st.secrets.get(env_key, ""))
    except Exception:
        return ""


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
    """プロバイダーに応じてAI APIを呼び出す共通関数"""
    if PROVIDER == "anthropic":
        return _call_anthropic(system_prompt, user_prompt, max_tokens)
    elif PROVIDER == "openai":
        return _call_openai(system_prompt, user_prompt, max_tokens)
    elif PROVIDER == "gemini":
        return _call_gemini(system_prompt, user_prompt, max_tokens)
    else:
        raise ValueError(f"未対応のプロバイダー: {PROVIDER}（anthropic / openai / gemini から選択）")


# ── Anthropic (Claude) ────────────────────────────────────
def _call_anthropic(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    import anthropic
    api_key = _get_api_key("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY が設定されていません")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


# ── OpenAI (GPT) ──────────────────────────────────────────
def _call_openai(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    from openai import OpenAI
    api_key = _get_api_key("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY が設定されていません")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


# ── Google Gemini ─────────────────────────────────────────
def _call_gemini(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    api_key = _get_api_key("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません")
    try:
        # 新しいSDK (google-genai) を優先して使う
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text or ""
    except ImportError:
        # 旧SDK (google-generativeai) にフォールバック
        import google.generativeai as genai_old
        genai_old.configure(api_key=api_key)
        model = genai_old.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            user_prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        return response.text
