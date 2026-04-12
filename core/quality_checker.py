"""品質チェックモジュール"""
from config import MIN_SECTION_CHARS, MAX_TITLE_CHARS, MAX_SUBTITLE_CHARS


def check_section_length(text: str, section_title: str) -> list[str]:
    issues = []
    text = text or ""
    length = len(text)
    if length < MIN_SECTION_CHARS:
        issues.append(
            f"【{section_title}】文字数不足: {length}文字 / 必要: {MIN_SECTION_CHARS}文字以上"
        )
    return issues


def check_title_length(title: str) -> list[str]:
    issues = []
    if len(title) > MAX_TITLE_CHARS:
        issues.append(f"タイトルが{MAX_TITLE_CHARS}文字超過: {len(title)}文字 → '{title}'")
    return issues


def check_subtitle_length(subtitle: str) -> list[str]:
    issues = []
    if len(subtitle) > MAX_SUBTITLE_CHARS:
        issues.append(
            f"サブタイトルが{MAX_SUBTITLE_CHARS}文字超過: {len(subtitle)}文字 → '{subtitle}'"
        )
    return issues


def check_duplication(sections: list[dict]) -> list[str]:
    """
    sections: [{"title": str, "text": str}, ...]
    先頭200文字が類似していたら重複の疑いを報告する（簡易版）
    """
    issues = []
    openings = [(s["title"], s["text"][:200]) for s in sections if s.get("text")]

    for i in range(len(openings)):
        for j in range(i + 1, len(openings)):
            t1, o1 = openings[i]
            t2, o2 = openings[j]
            # 共通語句が50文字以上連続していたら警告（単純チェック）
            common = _longest_common_substring(o1, o2)
            if len(common) >= 50:
                issues.append(
                    f"内容重複の可能性: 【{t1}】と【{t2}】の書き出しが類似しています"
                )
    return issues


def _longest_common_substring(s1: str, s2: str) -> str:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    longest = ""
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                if dp[i][j] > len(longest):
                    longest = s1[i - dp[i][j]: i]
            else:
                dp[i][j] = 0
    return longest


def check_text_truncation(text: str, section_title: str) -> list[str]:
    """
    文章が途中で切れていないかチェック。
    文末が句点・感嘆符・疑問符・閉じカッコ類で終わっていない場合は警告。
    """
    issues = []
    stripped = (text or "").rstrip()
    if not stripped:
        return issues
    valid_endings = ('。', '！', '？', '」', '』', '…', '☆', '★', '♪', '\n')
    if not stripped.endswith(valid_endings):
        tail = stripped[-30:].replace('\n', '↵')
        issues.append(
            f"【{section_title}】文章が途中で切れている可能性があります（末尾: 「...{tail}」）"
        )
    return issues


def run_all_checks(candidate: dict, sections: list[dict]) -> list[str]:
    """全チェックをまとめて実行してissueリストを返す"""
    issues = []
    issues += check_title_length(candidate.get("title", ""))
    issues += check_subtitle_length(candidate.get("subtitle", ""))
    for s in sections:
        issues += check_section_length(s.get("text", ""), s.get("title", ""))
        issues += check_text_truncation(s.get("text", ""), s.get("title", ""))
    issues += check_duplication(sections)
    return issues
