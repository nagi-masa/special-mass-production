"""
特典量産システム - Streamlit Webアプリ
起動: streamlit run web/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import streamlit as st
from datetime import datetime

from config import OUTPUT_DIR, MIN_SECTION_CHARS
from core.analyzer import analyze_materials
from core.candidate_generator import generate_candidates
from core.toc_generator import generate_toc, check_toc_validity
from core.content_generator import (
    generate_greeting,
    generate_intro,
    generate_section,
    generate_conclusion,
    generate_profile_page,
    generate_terms,
)
from core.cover_generator import generate_cover_assets
from core.quality_checker import run_all_checks
from core.word_exporter import export_report
from core.visuals_generator import generate_all_visuals_for_section
from core.project_store import new_project_id, save_project, list_projects

# ── ページ設定 ────────────────────────────────────────────
st.set_page_config(
    page_title="特典量産システム",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── セッション状態の初期化 ────────────────────────────────
STEPS = ["入力", "分析", "候補選択", "目次確認", "生成", "完了"]

def init_state():
    defaults = {
        "step": 0,
        "inputs": {},
        "analysis": {},
        "candidates_result": {},
        "selected_candidates": [],
        "current_candidate_idx": 0,
        "toc": {},
        "results": [],
        "project_id": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── サイドバー: APIキー設定 & ステップ表示 ──────────────
with st.sidebar:
    st.title("📄 特典量産システム")
    st.markdown("---")

    # ── APIキー設定 ──────────────────────────────────────
    st.subheader("🔑 APIキー設定")
    provider = st.selectbox(
        "AIプロバイダー",
        ["gemini", "anthropic", "openai"],
        index=0,
        help="使用するAIプロバイダーを選択してください",
    )
    api_key_input = st.text_input(
        "APIキー",
        type="password",
        placeholder="APIキーを入力してください",
        help=(
            "Gemini: https://aistudio.google.com/apikey\n"
            "Anthropic: https://console.anthropic.com/\n"
            "OpenAI: https://platform.openai.com/"
        ),
    )

    # セッション中にAPIキーをos.environに反映（動的読み込みに対応）
    if api_key_input:
        key_map = {
            "gemini": "GEMINI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
        }
        os.environ[key_map[provider]] = api_key_input
        os.environ["PROVIDER"] = provider
        st.success("APIキーを設定しました")
    elif not any(os.getenv(k) for k in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]):
        st.warning("APIキーを入力してください")

    st.markdown("---")
    st.subheader("進捗")
    for i, name in enumerate(STEPS):
        icon = "✅" if i < st.session_state.step else ("▶️" if i == st.session_state.step else "○")
        st.markdown(f"{icon} **ステップ{i+1}**: {name}")
    st.markdown("---")
    if st.button("🔄 最初からやり直す"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ─────────────────────────────────────────────────────────
# ステップ0: 入力
# ─────────────────────────────────────────────────────────
def step_input():
    st.header("ステップ1: 素材入力")
    st.caption("商品情報とテキスト素材を入力してください")

    with st.form("input_form"):
        st.markdown("**著者情報**")
        col_a, col_b = st.columns(2)
        with col_a:
            author_name = st.text_input("著者名 / 社名 *",
                placeholder="例: 山田 太郎 または 株式会社〇〇")
        with col_b:
            copyright_text = st.text_input("コピーライト表記（任意）",
                placeholder="例: © 2026 山田 太郎. All rights reserved.")
        author_profile = st.text_area("著者プロフィール（任意）", height=120,
            placeholder="例: 2015年に独立。フリーランスとして300社以上のマーケティング支援を行い、"
                         "クライアント継続率95%を達成。現在は同じ悩みを持つフリーランス向けに講座を提供。\n"
                         "※入力すると特典に合わせた内容にリライトされ、プロフィールページが生成されます。")

        st.markdown("---")
        product_name = st.text_input("商品名・セミナー名 *",
            placeholder="例: 副業で月10万円を目指すセミナー")
        target = st.text_input("ターゲット *",
            placeholder="例: 副業を始めたいが何から手をつければいいかわからない30代会社員")
        notes = st.text_area("補足メモ（任意）",
            placeholder="ターゲットの特徴、強調したい点など")

        st.markdown("---")
        st.markdown("**素材テキスト**（ブログ記事・文字起こし・アイデアメモなど）")
        mat1 = st.text_area("素材1 *", height=200,
            placeholder="ここにテキストを貼り付けてください")
        mat2 = st.text_area("素材2（任意）", height=150)
        mat3 = st.text_area("素材3（任意）", height=150)

        submitted = st.form_submit_button("分析開始 →", type="primary", use_container_width=True)

    if submitted:
        if not product_name or not target or not mat1:
            st.error("商品名・ターゲット・素材1は必須です")
            return
        if not author_name:
            st.error("著者名 / 社名は必須です")
            return
        # APIキーチェック
        key_map = {"gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
        active_provider = os.getenv("PROVIDER", "gemini")
        if not os.getenv(key_map.get(active_provider, "GEMINI_API_KEY")):
            st.error("サイドバーにAPIキーを入力してから分析を開始してください")
            return
        materials = [m for m in [mat1, mat2, mat3] if m.strip()]
        # コピーライトが空の場合はデフォルト生成
        from datetime import datetime as _dt
        year = _dt.now().year
        final_copyright = copyright_text.strip() if copyright_text.strip() else f"© {year} {author_name}. All rights reserved."
        st.session_state.inputs = {
            "product_name": product_name,
            "target": target,
            "notes": notes,
            "author_name": author_name,
            "copyright_text": final_copyright,
            "author_profile": author_profile.strip(),
            "materials": materials,
            "created_at": datetime.now().isoformat(),
        }
        st.session_state.project_id = new_project_id()
        st.session_state.step = 1
        st.rerun()


# ─────────────────────────────────────────────────────────
# ステップ1: 分析
# ─────────────────────────────────────────────────────────
def step_analyze():
    st.header("ステップ2: 素材分析")
    inputs = st.session_state.inputs

    if not st.session_state.analysis:
        with st.spinner("Claudeが素材を分析しています..."):
            analysis = analyze_materials(
                materials=inputs["materials"],
                product_name=inputs["product_name"],
                target=inputs["target"],
                notes=inputs["notes"],
            )
        st.session_state.analysis = analysis
        save_project(st.session_state.project_id, {
            **inputs,
            "project_id": st.session_state.project_id,
            "analysis": analysis,
        })

    analysis = st.session_state.analysis

    # 分析結果が空の場合はデバッグ情報を表示
    all_empty = not any([
        analysis.get("themes"),
        analysis.get("pain_points"),
        analysis.get("ideal_outcomes"),
        analysis.get("solutions"),
    ])
    if all_empty:
        st.error("分析結果が取得できませんでした。AIの応答を確認してください。")
        raw = analysis.get("raw_summary", "（応答なし）")
        with st.expander("AIの生応答を確認する（デバッグ用）", expanded=True):
            st.text(raw[:3000] if raw else "（空）")
        if st.button("再分析する", type="primary"):
            st.session_state.analysis = {}
            st.rerun()
        return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("抽出されたテーマ")
        for t in analysis.get("themes", []):
            st.markdown(f"- {t}")
        st.subheader("読者の悩み")
        for p in analysis.get("pain_points", []):
            st.markdown(f"- {p}")
    with col2:
        st.subheader("読者の理想")
        for o in analysis.get("ideal_outcomes", []):
            st.markdown(f"- {o}")
        st.subheader("解決策")
        for s in analysis.get("solutions", []):
            st.markdown(f"- {s}")

    if st.button("特典候補を生成する →", type="primary", use_container_width=True):
        st.session_state.step = 2
        st.rerun()


# ─────────────────────────────────────────────────────────
# ステップ2: 候補選択
# ─────────────────────────────────────────────────────────
def step_candidates():
    st.header("ステップ3: 特典候補選択")

    inputs = st.session_state.inputs
    analysis = st.session_state.analysis

    if not st.session_state.candidates_result:
        with st.spinner("特典候補を生成しています..."):
            result = generate_candidates(analysis, inputs["product_name"], inputs["target"])
        st.session_state.candidates_result = result

    result = st.session_state.candidates_result

    if not result.get("can_multiply"):
        st.warning(f"この素材は1本向きと判定されました。\n理由: {result.get('reason', '')}")
    else:
        st.success(f"{len(result.get('candidates', []))}件の候補を生成しました")

    candidates = result.get("candidates", [])
    if not candidates:
        st.error("候補が生成されませんでした。素材を確認してください。")
        return

    st.markdown("---")
    selected_ids = []
    for c in candidates:
        with st.expander(f"**No.{c['id']} {c['title']}**", expanded=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**サブタイトル:** {c.get('subtitle', '')}")
                st.markdown(f"**コンセプト:** {c.get('concept', '')}")
                st.markdown(f"**ターゲットの悩み:** {c.get('target_pain', '')}")
                st.markdown(f"**ターゲットの理想:** {c.get('target_ideal', '')}")
            with col2:
                for badge in c.get("badges", []):
                    st.markdown(f"🏷️ **{badge}**")
            if st.checkbox(f"この特典を作る", key=f"sel_{c['id']}"):
                selected_ids.append(c["id"])

    if st.button("選択した特典の目次を生成する →", type="primary", use_container_width=True):
        if not selected_ids:
            st.error("1つ以上選択してください")
            return
        selected = [c for c in candidates if c["id"] in selected_ids][:5]
        st.session_state.selected_candidates = selected
        st.session_state.current_candidate_idx = 0
        st.session_state.step = 3
        st.rerun()


# ─────────────────────────────────────────────────────────
# ステップ3: 目次確認
# ─────────────────────────────────────────────────────────
def step_toc():
    # ページ最上部にスクロール
    st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)

    selected = st.session_state.selected_candidates
    idx = st.session_state.current_candidate_idx
    candidate = selected[idx]
    analysis = st.session_state.analysis
    target = st.session_state.inputs["target"]

    # 進捗バーで何本目かを明示
    st.progress((idx) / len(selected), text=f"目次確認の進捗: {idx+1} / {len(selected)} 本目")

    # 大きく番号とタイトルを表示
    st.markdown(f"""
<div style="background:#1e3a5f;color:white;padding:20px;border-radius:10px;margin-bottom:20px;">
    <h2 style="margin:0;color:white;">📋 {idx+1} / {len(selected)} 本目の目次確認</h2>
    <p style="margin:8px 0 0 0;font-size:18px;">{candidate['title']}</p>
</div>
""", unsafe_allow_html=True)

    st.header("ステップ4: 目次確認・編集")

    toc_key = f"toc_{candidate['id']}"
    if toc_key not in st.session_state:
        with st.spinner("目次を生成しています..."):
            toc = generate_toc(candidate, analysis, target)
        st.session_state[toc_key] = toc

    toc = st.session_state[toc_key]
    issues = check_toc_validity(toc)
    if issues:
        for issue in issues:
            st.warning(issue)

    st.markdown("---")
    st.subheader("目次案（編集可能）")

    edited_sections = []
    for s in toc.get("sections", []):
        with st.expander(f"第{s['number']}章: {s['title']}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                new_title = st.text_input("タイトル", value=s["title"], key=f"t_{candidate['id']}_{s['number']}")
                new_role = st.text_input("役割", value=s.get("role", ""), key=f"r_{candidate['id']}_{s['number']}")
            with col2:
                new_summary = st.text_area("概要", value=s.get("summary", ""), key=f"s_{candidate['id']}_{s['number']}", height=80)
            edited_sections.append({
                "number": s["number"],
                "title": new_title,
                "role": new_role,
                "summary": new_summary,
            })

    col_back, col_ok = st.columns(2)
    with col_back:
        if st.button("← 候補選択に戻る"):
            st.session_state.step = 2
            st.rerun()
    with col_ok:
        btn_label = "この目次で生成開始 →" if idx == len(selected) - 1 else f"この目次を確定して次の特典へ ({idx+2}/{len(selected)})"
        if st.button(btn_label, type="primary", use_container_width=True):
            toc["sections"] = edited_sections
            st.session_state[toc_key] = toc

            if idx < len(selected) - 1:
                next_title = selected[idx + 1]["title"]
                st.session_state.current_candidate_idx += 1
                st.toast(f"✅ {idx+1}本目の目次を確定しました。次: {next_title}", icon="📋")
                st.rerun()
            else:
                st.session_state.step = 4
                st.rerun()


# ─────────────────────────────────────────────────────────
# ステップ4: 生成
# ─────────────────────────────────────────────────────────
def step_generate():
    st.header("ステップ5: レポート生成中")

    selected = st.session_state.selected_candidates
    target = st.session_state.inputs["target"]
    analysis = st.session_state.analysis
    project_id = st.session_state.project_id

    results = []
    progress_bar = st.progress(0)
    status = st.empty()

    for i, candidate in enumerate(selected):
        toc = st.session_state.get(f"toc_{candidate['id']}", {})
        safe_title = candidate["title"].replace("/", "_").replace("\\", "_")[:20]
        out_dir = OUTPUT_DIR / project_id
        out_dir.mkdir(parents=True, exist_ok=True)

        status.info(f"**{i+1}/{len(selected)}: {candidate['title']}** を生成中...")

        with st.spinner("あいさつ・はじめに を生成中..."):
            greeting = generate_greeting(candidate, target)
            intro = generate_intro(candidate, target)

        sections_data = []
        section_visuals = {}
        generated_texts = []
        section_list = toc.get("sections", [])
        total_steps = len(section_list) + 2  # +あいさつ+おわりに

        for j, section in enumerate(section_list):
            status.info(f"**{candidate['title']}** - 第{section['number']}章「{section['title']}」を生成中...")
            progress_bar.progress((i / len(selected)) + (j / total_steps / len(selected)))

            text = generate_section(section, candidate, target, generated_texts)
            generated_texts.append(text)
            sections_data.append({"number": section["number"], "title": section["title"], "text": text})

            # 図解生成
            visuals = generate_all_visuals_for_section(section, text, candidate, target, out_dir)
            section_visuals[section["number"]] = visuals

        with st.spinner("おわりに・表紙素材を生成中..."):
            conclusion = generate_conclusion(candidate, target, generated_texts)
            cover_assets = generate_cover_assets(candidate, target)
            author_name = st.session_state.inputs.get("author_name", "")
            copyright_text = st.session_state.inputs.get("copyright_text", "")
            raw_profile = st.session_state.inputs.get("author_profile", "")
            terms = generate_terms(
                author_name=author_name,
                report_title=candidate.get("title", ""),
            )

        # 著者プロフィール（入力がある場合のみAIでリライト）
        profile_page = ""
        if raw_profile:
            with st.spinner("著者プロフィールをリライト中..."):
                profile_page = generate_profile_page(candidate, raw_profile, target)

        issues = run_all_checks({**candidate, **cover_assets}, sections_data)

        word_path = out_dir / f"{safe_title}.docx"
        export_report(
            output_path=word_path,
            candidate=candidate,
            cover_assets=cover_assets,
            greeting=greeting,
            intro=intro,
            sections=sections_data,
            conclusion=conclusion,
            terms=terms,
            section_visuals=section_visuals,
            author_name=author_name,
            copyright_text=copyright_text,
            profile_page=profile_page,
        )

        results.append({
            "candidate": candidate,
            "word_path": str(word_path),
            "quality_issues": issues,
        })
        progress_bar.progress((i + 1) / len(selected))

    st.session_state.results = results
    save_project(project_id, {
        "project_id": project_id,
        **st.session_state.inputs,
        "analysis": analysis,
        "results": results,
    })
    st.session_state.step = 5
    st.rerun()


# ─────────────────────────────────────────────────────────
# ステップ5: 完了・ダウンロード
# ─────────────────────────────────────────────────────────
def step_done():
    st.header("✅ 生成完了")
    st.success(f"{len(st.session_state.results)}本の特典レポートが生成されました！")

    for result in st.session_state.results:
        candidate = result["candidate"]
        word_path = Path(result["word_path"])
        issues = result.get("quality_issues", [])

        with st.expander(f"📄 {candidate['title']}", expanded=True):
            if issues:
                st.warning("品質上の注意点:\n" + "\n".join(f"- {i}" for i in issues))
            else:
                st.success("品質チェック通過")

            if word_path.exists():
                with open(word_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ {word_path.name} をダウンロード",
                        data=f,
                        file_name=word_path.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )

    st.markdown("---")
    if st.button("🆕 新しい特典を作る", type="primary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ─────────────────────────────────────────────────────────
# ルーティング
# ─────────────────────────────────────────────────────────
step = st.session_state.step
if step == 0:
    step_input()
elif step == 1:
    step_analyze()
elif step == 2:
    step_candidates()
elif step == 3:
    step_toc()
elif step == 4:
    step_generate()
elif step == 5:
    step_done()
