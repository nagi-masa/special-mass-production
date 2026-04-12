"""
特典量産システム - FastAPI バックエンド
起動: uvicorn api.main:app --reload --port 8000
"""
import asyncio
import sys
from pathlib import Path

# core/ を参照できるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    MaterialInput,
    CandidateSelectInput,
    TocGenerateInput,
    GenerateReportInput,
)
from config import OUTPUT_DIR
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
from core.project_store import new_project_id, save_project, load_project, list_projects

app = FastAPI(title="特典量産システム API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── プロジェクト管理 ──────────────────────────────────────
@app.get("/projects")
async def get_projects():
    return list_projects()


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    try:
        return load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "案件が見つかりません")


# ── ステップ1: 素材分析 ────────────────────────────────────
@app.post("/analyze")
async def analyze(body: MaterialInput):
    result = await asyncio.to_thread(
        analyze_materials,
        body.materials, body.product_name, body.target, body.notes
    )
    return result


# ── ステップ2: 候補生成 ────────────────────────────────────
@app.post("/candidates")
async def candidates(body: CandidateSelectInput):
    result = await asyncio.to_thread(
        generate_candidates,
        body.analysis, body.product_name, body.target
    )
    return result


# ── ステップ3: 目次生成 ────────────────────────────────────
@app.post("/toc")
async def toc(body: TocGenerateInput):
    result = await asyncio.to_thread(
        generate_toc,
        body.candidate, body.analysis, body.target
    )
    issues = check_toc_validity(result)
    return {"toc": result, "issues": issues}


# ── ステップ4: レポート全文生成 ─────────────────────────────
@app.post("/generate")
async def generate(body: GenerateReportInput):
    project_id = body.project_id
    candidate = body.candidate
    toc = body.toc
    target = body.target

    safe_title = candidate["title"].replace("/", "_").replace("\\", "_")[:20]
    out_dir = OUTPUT_DIR / project_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # あいさつ・はじめに
    greeting = await asyncio.to_thread(generate_greeting, candidate, target)
    intro = await asyncio.to_thread(generate_intro, candidate, target)

    # 本文各章
    sections_data = []
    section_visuals = {}
    generated_texts = []

    for section in toc.get("sections", []):
        text = await asyncio.to_thread(
            generate_section, section, candidate, target, generated_texts
        )
        generated_texts.append(text)
        sections_data.append({"number": section["number"], "title": section["title"], "text": text})

        if body.generate_visuals:
            visuals = await asyncio.to_thread(
                generate_all_visuals_for_section,
                section, text, candidate, target, out_dir
            )
            section_visuals[section["number"]] = visuals

    conclusion = await asyncio.to_thread(generate_conclusion, candidate, target, generated_texts)
    cover_assets = await asyncio.to_thread(generate_cover_assets, candidate, target)
    terms = generate_terms(
        author_name=body.author_name,
        report_title=candidate.get("title", ""),
    )

    # 著者プロフィール（入力がある場合のみリライト）
    profile_page = ""
    if body.author_profile:
        profile_page = await asyncio.to_thread(
            generate_profile_page, candidate, body.author_profile, target
        )

    # 品質チェック
    issues = run_all_checks({**candidate, **cover_assets}, sections_data)

    # Word出力
    word_path = out_dir / f"{safe_title}.docx"
    await asyncio.to_thread(
        export_report,
        word_path, candidate, cover_assets,
        greeting, intro, sections_data, conclusion, terms,
        section_visuals if body.generate_visuals else None,
        body.author_name,
        body.copyright_text,
        profile_page,
    )

    result = {
        "project_id": project_id,
        "word_path": str(word_path),
        "quality_issues": issues,
        "sections_count": len(sections_data),
        "visuals_count": sum(
            sum(1 for v in vs if v.get("path")) for vs in section_visuals.values()
        ) if section_visuals else 0,
    }

    # 保存
    try:
        data = load_project(project_id)
    except FileNotFoundError:
        data = {"project_id": project_id, "target": target}
    data.setdefault("results", []).append(result)
    save_project(project_id, data)

    return result


# ── ダウンロード ────────────────────────────────────────────
@app.get("/download/{project_id}/{filename}")
async def download(project_id: str, filename: str):
    path = OUTPUT_DIR / project_id / filename
    if not path.exists():
        raise HTTPException(404, "ファイルが見つかりません")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
