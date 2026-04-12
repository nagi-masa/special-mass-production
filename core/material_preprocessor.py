"""
素材テキスト前処理モジュール（Pythonのみ・AIトークンゼロ）

目的:
  AIに渡す前に素材テキストを圧縮・クリーニングすることで
  analyze_materials() のAPIコスト・レイテンシを削減する。

処理内容（すべてPython・判断不要な機械処理）:
  1. 空白・改行の正規化
  2. 重複行・重複段落の除去
  3. 1素材あたり上限文字数でトリム（先頭70%+末尾30%を保持）
  4. 複数素材の連結サイズを全体上限でトリム
"""
import re


_MAX_PER_MATERIAL = 3000   # 1素材あたりの最大文字数
_MAX_TOTAL = 8000          # 全素材合計の最大文字数


def _normalize_whitespace(text: str) -> str:
    """連続する空白行を1行にまとめ、行末スペースを除去する"""
    # 3行以上の空行 → 2行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 行末の空白除去
    lines = [line.rstrip() for line in text.split('\n')]
    return '\n'.join(lines).strip()


def _remove_duplicate_paragraphs(text: str) -> str:
    """
    完全一致の重複段落を除去する。
    段落 = 空行で区切られたブロック。
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    seen = []
    unique = []
    for p in paragraphs:
        # 短い段落（50文字以下）は重複チェックしない（挨拶文等を保持）
        key = p if len(p) > 50 else None
        if key is None or key not in seen:
            unique.append(p)
            if key:
                seen.append(key)
    return '\n\n'.join(unique)


def _smart_trim(text: str, max_chars: int) -> str:
    """
    長すぎるテキストを先頭70%+末尾30%で保持する。
    （冒頭の主張と末尾のまとめ・CTAを残すため）
    """
    if len(text) <= max_chars:
        return text
    head_chars = int(max_chars * 0.7)
    tail_chars = max_chars - head_chars
    head = text[:head_chars]
    tail = text[-tail_chars:]
    # 段落境界で切る
    head_cut = head.rfind('\n\n')
    if head_cut > head_chars * 0.5:
        head = head[:head_cut]
    tail_cut = tail.find('\n\n')
    if tail_cut >= 0 and tail_cut < tail_chars * 0.5:
        tail = tail[tail_cut:]
    return head + '\n\n…（中略）…\n\n' + tail


def preprocess_material(text: str) -> str:
    """1素材を前処理して返す"""
    text = _normalize_whitespace(text)
    text = _remove_duplicate_paragraphs(text)
    text = _smart_trim(text, _MAX_PER_MATERIAL)
    return text


def preprocess_materials(materials: list[str]) -> list[str]:
    """
    素材リストを前処理して返す。
    合計文字数が _MAX_TOTAL を超える場合は各素材を均等に圧縮する。
    """
    if not materials:
        return []

    # 各素材を個別に前処理
    processed = [preprocess_material(m) for m in materials if m.strip()]

    # 合計サイズチェック
    total = sum(len(p) for p in processed)
    if total > _MAX_TOTAL and len(processed) > 0:
        # 各素材を均等に圧縮
        per_limit = _MAX_TOTAL // len(processed)
        processed = [_smart_trim(p, per_limit) for p in processed]

    return processed


def get_stats(original: list[str], processed: list[str]) -> dict:
    """前処理前後の統計情報を返す（ログ用）"""
    orig_total = sum(len(m) for m in original)
    proc_total = sum(len(p) for p in processed)
    return {
        "original_chars": orig_total,
        "processed_chars": proc_total,
        "reduction_pct": round((1 - proc_total / orig_total) * 100, 1) if orig_total > 0 else 0,
    }
