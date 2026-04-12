"""JSON抽出ユーティリティ - AIレスポンスからJSONを堅牢に取り出す"""
import json
import re


def extract_json(raw: str, fallback: dict = None) -> dict:
    """
    AIの応答文字列からJSONオブジェクトを堅牢に抽出する。

    試行順序:
    1. ```json ... ``` コードブロック
    2. ``` ... ``` コードブロック（言語指定なし）
    3. 最初の { から対応する } までをネスト深度で追跡
    失敗した場合は fallback を返す。
    """
    if fallback is None:
        fallback = {}

    # 1. ```json ... ``` コードブロック
    for pattern in [
        r"```json\s*(\{.*?\})\s*```",
        r"```\s*(\{.*?\})\s*```",
    ]:
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

    # 2. ネスト深度を追跡して { } を正確に抽出
    try:
        start = raw.index("{")
        depth = 0
        for i, ch in enumerate(raw[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(raw[start:i + 1])
    except (ValueError, json.JSONDecodeError):
        pass

    print(f"[json_utils] JSON抽出失敗。先頭200文字: {raw[:200]}")
    return fallback
