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


def call_claude(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
    json_mode: bool = False,
    disable_thinking: bool = False,
) -> str:
    """プロバイダーに応じてAI APIを呼び出す共通関数

    json_mode=True       : JSONを返す呼び出し。Gemini では response_mime_type="application/json"
                           + thinking無効化で出力トークンを最大確保する。
    disable_thinking=True: 長文生成など、thinking不要な呼び出しで出力トークンを最大確保する。
                           json_mode=True のときも自動的にdisable_thinking扱いになる。
    """
    if PROVIDER == "anthropic":
        return _call_anthropic(system_prompt, user_prompt, max_tokens)
    elif PROVIDER == "openai":
        return _call_openai(system_prompt, user_prompt, max_tokens, json_mode=json_mode)
    elif PROVIDER == "gemini":
        return _call_gemini(
            system_prompt, user_prompt, max_tokens,
            json_mode=json_mode,
            disable_thinking=disable_thinking or json_mode,
        )
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


def _set_thinking_budget_zero(config_kwargs: dict, types_module) -> None:
    """
    Gemini の thinking を無効化する。
    SDK バージョンごとに API が異なるため、複数の方法を順番に試す。
    """
    # 方法1: types.ThinkingConfig(thinking_budget=0)
    try:
        config_kwargs["thinking_config"] = types_module.ThinkingConfig(thinking_budget=0)
        return
    except Exception:
        pass
    # 方法2: dict 形式（旧バージョンの SDK）
    try:
        config_kwargs["thinking_config"] = {"thinkingBudget": 0}
        return
    except Exception:
        pass
    # 方法3: include_thoughts=False（代替パラメータ）
    try:
        config_kwargs["thinking_config"] = types_module.ThinkingConfig(include_thoughts=False)
    except Exception:
        pass  # すべて失敗してもエラーにしない（max_tokens 増量でカバー）


# ── Google Gemini ─────────────────────────────────────────
def _call_gemini(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    json_mode: bool = False,
    disable_thinking: bool = False,
) -> str:
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

        # Gemini 2.5 Flash はデフォルトで thinking トークンを消費し、
        # max_output_tokens の枠を圧迫する。json_mode または長文生成では
        # thinking を無効化して出力トークンを最大確保する。
        if disable_thinking or json_mode:
            _set_thinking_budget_zero(config_kwargs, types)

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
