"""本文生成モジュール：セクション単位で生成・重複チェックつき・自動再生成対応"""
import json
from core.claude_client import call_claude
from core.quality_checker import check_text_truncation
from config import PROMPTS_DIR, MIN_SECTION_CHARS

MAX_RETRIES = 2  # 文字数不足時の最大再試行回数


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def generate_greeting(candidate: dict, target: str) -> str:
    system_prompt = load_prompt("generate_section.md")
    user_prompt = f"""
# パート: あいさつ
# 特典タイトル: {candidate["title"]}
# ターゲット: {target}
著者からの温かい挨拶文を800文字程度で書いてください。
"""
    return call_claude(system_prompt, user_prompt, max_tokens=2500)


def generate_intro(candidate: dict, target: str) -> str:
    system_prompt = load_prompt("generate_section.md")
    user_prompt = f"""
# パート: はじめに
# 特典タイトル: {candidate["title"]}
# コンセプト: {candidate.get("concept", "")}
# ターゲットの悩み: {candidate.get("target_pain", "")}
# ターゲットの理想: {candidate.get("target_ideal", "")}
# ターゲット: {target}
読者が「これは自分のことだ」と感じる導入文を1500文字以上で書いてください。
冒頭の1〜2文で読者の「あるある」をズバリ突くこと。
「〜ではありませんか？」「〜と感じていませんか？」で読者を引き込み、
この特典を読むと何が変わるかを具体的に示すこと。
絶対に途中で切らず、最後まで書き切ること。
"""
    return call_claude(system_prompt, user_prompt, max_tokens=4000)


def _build_section_prompt(
    section: dict,
    candidate: dict,
    target: str,
    previous_sections: list[str],
    attempt: int = 0,
) -> str:
    prev_summary = ""
    if previous_sections:
        prev_summary = "【すでに書いた章の概要（内容を繰り返さないこと）】\n"
        for i, p in enumerate(previous_sections, 1):
            prev_summary += f"第{i}章の冒頭200文字: {p[:200]}\n"

    retry_note = ""
    if attempt > 0:
        retry_note = f"""
【重要・再生成{attempt}回目】前回の生成に問題がありました（文字数不足または文章が途中で切れていた）。
今回は必ず2500文字以上で書き、必ず「。」で終わる完結した文章にしてください。
文章を途中で絶対に切らないこと。具体的なエピソード・会話・体験談・事例をさらに詳しく書き込んでください。
"""

    return f"""
# パート: 本文
# 章番号: 第{section["number"]}章
# 章タイトル: {section["title"]}
# ストーリー上の役割: {section.get("role", "")}
# 章の概要: {section.get("summary", "")}
# 特典タイトル: {candidate["title"]}
# ターゲット: {target}
# ターゲットの悩み: {candidate.get("target_pain", "")}

{prev_summary}
{retry_note}
2500文字以上で書いてください。
読者が疑似体験できるよう、具体的な場面・事例・対話を交えてください。
抽象論だけで終わらず、読者が明日から動ける内容にしてください。
"""


def generate_section(
    section: dict,
    candidate: dict,
    target: str,
    previous_sections: list[str],
    on_retry: callable = None,
) -> str:
    """
    本文1章を生成する。文字数不足時は自動再生成する。
    previous_sections: すでに生成済みの章テキストのリスト（重複防止用）
    on_retry: 再生成時に呼ばれるコールバック(attempt, current_len)
    """
    system_prompt = load_prompt("generate_section.md")

    for attempt in range(MAX_RETRIES + 1):
        user_prompt = _build_section_prompt(section, candidate, target, previous_sections, attempt)
        text = call_claude(system_prompt, user_prompt, max_tokens=5000)

        is_truncated = bool(check_text_truncation(text, section.get("title", "")))
        if len(text) >= MIN_SECTION_CHARS and not is_truncated:
            return text

        if attempt < MAX_RETRIES:
            if on_retry:
                on_retry(attempt + 1, len(text))
        # 最終試行まで問題があっても最後の結果を返す

    return text


def generate_conclusion(candidate: dict, target: str, sections: list[str]) -> str:
    system_prompt = load_prompt("generate_section.md")
    user_prompt = f"""
# パート: おわりに
# 特典タイトル: {candidate["title"]}
# ターゲット: {target}
各章の学びをまとめ、読者を自然に次の行動に促す結びの文章を1000文字程度で書いてください。
売り込みではなく、読者への応援メッセージとして書いてください。
"""
    return call_claude(system_prompt, user_prompt, max_tokens=2000)


def generate_profile_page(candidate: dict, author_profile: str, target: str) -> str:
    """
    著者プロフィールをこの特典のターゲットに合わせてリライトする。
    読者が「この人の話なら聞きたい」と感じる内容に調整する。
    """
    system_prompt = load_prompt("generate_section.md")
    user_prompt = f"""
# パート: 著者プロフィール（リライト）
# 特典タイトル: {candidate["title"]}
# ターゲット: {target}
# ターゲットの悩み: {candidate.get("target_pain", "")}

# 元のプロフィール:
{author_profile}

以下の条件でプロフィールをリライトしてください：
- ターゲット（{target}）に対して「信頼・権威・共感」を感じてもらえる内容に調整する
- 著者の経歴・実績をこの特典のテーマに関連付けて語る
- 「この人だからこそ教えられる」というストーリーを作る
- 読者が「この人の話なら聞きたい」と感じる温かみのある文体
- 800〜1000文字程度
- 「です・ます」調
- 箇条書きではなく、連続した文章で書く
"""
    return call_claude(system_prompt, user_prompt, max_tokens=2000)


def generate_terms(author_name: str = "", report_title: str = "", court: str = "大阪地方裁判所") -> str:
    author = author_name or "著者"
    title = report_title or "本特典"
    return f"""特典利用規約

第1条（目的）
本規約は、{author}（以下「著者」といいます）が発行する特典「{title}」（以下「本特典」といいます）の利用条件を定めるものです。

利用者は、本特典をダウンロードまたは閲覧した時点で、本規約のすべての条項に同意したものとみなされます。

第2条（著作権の帰属）
本特典に含まれる文章、画像、図表、デザイン等の著作権は、著者に帰属します。

著作権法により認められる「引用」の範囲を超えて、著者の事前の書面による承諾なく、本特典の内容を利用することはできません。

第3条（禁止事項）
利用者は、本特典の利用にあたり、以下の行為を行ってはなりません。

（1）本特典の全部または一部を、無断で複製、転載、公衆送信（SNSやブログへのアップロード等）、改変する行為。
（2）本特典をあたかも利用者が作成したかのように装って公表する行為（自作発言）。
（3）本特典を有償・無償を問わず第三者に転売、配布、貸与、または自身の特典として利用する行為。
（4）著者または第三者の名誉、信用、または知的財産権を侵害する行為。

第4条（利用の範囲）
利用者は、本特典を自己の学習または参考とする目的（私的利用）に限り、閲覧および保存することができます。

商用目的での利用や、法人内での共有を希望する場合は、別途著者の承諾を得るものとします。

第5条（免責事項）
著者は、本特典の内容の正確性、有用性、最新性等について細心の注意を払っておりますが、これらを保証するものではありません。

本特典の利用によって生じた直接的または間接的な損害（データの消失、利益の損失等）について、著者は一切の責任を負いません。

第6条（規約の変更）
著者は、必要と判断した場合には、利用者に通知することなくいつでも本規約を変更することができるものとします。

第7条（準拠法および管轄）
本規約の解釈にあたっては、日本法を準拠法とします。
本特典の利用に関して紛争が生じた場合には、{court}を第一審の専属的合意管轄裁判所とします。


以上
"""
