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


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 4096, json_mode: bool = False) -> str:
    """プロバイダーに応じてAI APIを呼び出す共通関数

    json_mode=True: JSONを返すことが確実な呼び出しに使用。
    Gemini では response_mime_type="application/json" + thinking無効化で
    出力トークンを最大確保する。
    """
    if PROVIDER == "anthropic":
        return _call_anthropic(system_prompt, user_prompt, max_tokens)
    elif PROVIDER == "openai":
        return _call_openai(system_prompt, user_prompt, max_tokens, json_mode=json_mode)
    elif PROVIDER == "gemini":
        return _call_gemini(system_prompt, user_prompt, max_tokens, json_mode=json_mode)
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
def _call_openai(system_prompt: str, user_prompt: str, max_tokens: int, json_mode: bool = False) -> str:
    from openai import OpenAI
    api_key = _get_api_key("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY が設定されていません")
    client = OpenAI(api_key=api_key)
    kwargs = dict(
        model=OPENAI_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


# ── Google Gemini ─────────────────────────────────────────
def _call_gemini(system_prompt: str, user_prompt: str, max_tokens: int, json_mode: bool = False) -> str:
    api_key = _get_api_key("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません")
    try:
        # 新しいSDK (google-genai) を優先して使う
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)

        config_kwargs: dict = dict(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
        )
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
            # Gemini 2.5 Flash はデフォルトで thinking トークンを消費する。
            # JSON専用呼び出しでは thinking を無効化して出力トークンを最大確保する。
            try:
                config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            except Exception:
                pass  # SDKバージョンが非対応でも続行

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(**config_kwargs),
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
        gen_config: dict = {"max_output_tokens": max_tokens}
        if json_mode:
            gen_config["response_mime_type"] = "application/json"
        response = model.generate_content(
            user_prompt,
            generation_config=gen_config,
        )
        return response.text
