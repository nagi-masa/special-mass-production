"""
特典量産システム - ローカルCLI版
実行: python main.py
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import OUTPUT_DIR, MIN_SECTION_CHARS
from core.analyzer import analyze_materials
from core.candidate_generator import generate_candidates
from core.toc_generator import generate_toc, check_toc_validity
from core.content_generator import (
    generate_greeting,
    generate_intro,
    generate_section,
    generate_conclusion,
    generate_terms,
)
from core.cover_generator import generate_cover_assets
from core.quality_checker import run_all_checks
from core.word_exporter import export_report
from core.visuals_generator import generate_all_visuals_for_section
from core.project_store import new_project_id, save_project, list_projects

console = Console()


# ──────────────────────────────────────────────────────────
# ステップ1: 入力収集
# ──────────────────────────────────────────────────────────
def collect_inputs() -> dict:
    console.print(Panel("[bold cyan]特典量産システム[/bold cyan]\nステップ1: 素材入力", expand=False))

    product_name = Prompt.ask("商品名・セミナー名")
    target = Prompt.ask("ターゲット（例: 副業を始めたい30代会社員）")
    notes = Prompt.ask("補足メモ（なければEnter）", default="")

    console.print("\n[bold]素材テキストを入力してください。[/bold]")
    console.print("複数ある場合は1つずつ入力し、最後に 'END' と入力してください。")
    console.print("（ブログ記事・文字起こし・アイデアメモなど何でも可）\n")

    materials = []
    while True:
        console.print(f"[dim]素材 {len(materials)+1} を入力（'END'で終了）:[/dim]")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        text = "\n".join(lines).strip()
        if text:
            materials.append(text)
            console.print(f"[green]✓ 素材{len(materials)}を受け付けました（{len(text)}文字）[/green]")

        if not Confirm.ask("さらに素材を追加しますか？"):
            break

    if not materials:
        console.print("[red]素材が入力されていません。終了します。[/red]")
        sys.exit(1)

    return {
        "product_name": product_name,
        "target": target,
        "notes": notes,
        "materials": materials,
        "created_at": datetime.now().isoformat(),
    }


# ──────────────────────────────────────────────────────────
# ステップ2: 素材分析
# ──────────────────────────────────────────────────────────
def step_analyze(inputs: dict) -> dict:
    console.print("\n[bold cyan]ステップ2: 素材分析中...[/bold cyan]")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as p:
        p.add_task("Claudeが素材を分析しています...")
        analysis = analyze_materials(
            materials=inputs["materials"],
            product_name=inputs["product_name"],
            target=inputs["target"],
            notes=inputs["notes"],
        )

    console.print("[green]✓ 分析完了[/green]")
    console.print(f"  テーマ: {analysis.get('themes', [])}")
    console.print(f"  悩み: {analysis.get('pain_points', [])}")
    console.print(f"  理想: {analysis.get('ideal_outcomes', [])}")
    return analysis


# ──────────────────────────────────────────────────────────
# ステップ3: 特典候補生成
# ──────────────────────────────────────────────────────────
def step_generate_candidates(inputs: dict, analysis: dict) -> dict:
    console.print("\n[bold cyan]ステップ3: 特典候補生成中...[/bold cyan]")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as p:
        p.add_task("候補を生成しています...")
        result = generate_candidates(analysis, inputs["product_name"], inputs["target"])

    if not result.get("can_multiply"):
        console.print(Panel(
            f"[yellow]この素材は1本向きと判定されました。\n理由: {result.get('reason', '')}[/yellow]",
            title="複数展開の判定"
        ))
    else:
        console.print(f"[green]✓ {len(result.get('candidates', []))}件の候補を生成しました[/green]")

    return result


# ──────────────────────────────────────────────────────────
# ステップ4: 候補選択
# ──────────────────────────────────────────────────────────
def step_select_candidates(candidates_result: dict) -> list[dict]:
    candidates = candidates_result.get("candidates", [])
    if not candidates:
        console.print("[red]候補が生成されませんでした。[/red]")
        sys.exit(1)

    console.print("\n[bold cyan]ステップ4: 特典候補を選んでください[/bold cyan]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("No.", width=4)
    table.add_column("タイトル", width=35)
    table.add_column("サブタイトル", width=45)
    table.add_column("バッジ", width=30)

    for c in candidates:
        badges = "　".join(c.get("badges", []))
        table.add_row(str(c["id"]), c.get("title", ""), c.get("subtitle", ""), badges)

    console.print(table)

    selected_ids_str = Prompt.ask(
        "\n作る特典の番号をカンマ区切りで入力してください（例: 1,3）\n最大5件まで"
    )
    try:
        selected_ids = [int(x.strip()) for x in selected_ids_str.split(",")]
    except ValueError:
        console.print("[red]入力が正しくありません。[/red]")
        sys.exit(1)

    selected = [c for c in candidates if c["id"] in selected_ids][:5]
    console.print(f"[green]✓ {len(selected)}件を選択しました[/green]")
    return selected


# ──────────────────────────────────────────────────────────
# 目次手動編集ヘルパー
# ──────────────────────────────────────────────────────────
def _edit_toc_in_editor(toc: dict, out_dir: Path, console: Console) -> dict:
    """目次をテキストファイルに書き出してエディタで編集→読み返す"""
    edit_file = out_dir / "toc_edit.txt"
    edit_file.parent.mkdir(parents=True, exist_ok=True)

    # テキストファイルに書き出す
    lines = [
        "# 目次編集ファイル",
        "# タイトル・役割・概要を自由に編集してください。",
        "# 章を追加する場合は同じ形式でブロックを追加してください。",
        "# 保存後、このターミナルに戻ってEnterを押してください。",
        "",
    ]
    for s in toc.get("sections", []):
        lines += [
            f"## 第{s['number']}章",
            f"タイトル: {s.get('title', '')}",
            f"役割: {s.get('role', '')}",
            f"概要: {s.get('summary', '')}",
            "",
        ]
    edit_file.write_text("\n".join(lines), encoding="utf-8")

    # デフォルトエディタで開く
    console.print(f"\n[cyan]目次ファイルを開きます: {edit_file}[/cyan]")
    try:
        if os.name == "nt":
            os.startfile(str(edit_file))
        else:
            subprocess.Popen(["xdg-open", str(edit_file)])
    except Exception:
        console.print(f"[yellow]自動で開けませんでした。手動で開いてください: {edit_file}[/yellow]")

    input("\n編集・保存が完了したらEnterを押してください...")

    # 読み返してパース
    content = edit_file.read_text(encoding="utf-8")
    sections = []
    current: dict = {}
    for line in content.splitlines():
        if line.startswith("## 第"):
            if "title" in current:
                sections.append(current)
            try:
                num = int(line.replace("## 第", "").replace("章", "").strip())
            except ValueError:
                num = len(sections) + 1
            current = {"number": num}
        elif line.startswith("タイトル:"):
            current["title"] = line.replace("タイトル:", "").strip()
        elif line.startswith("役割:"):
            current["role"] = line.replace("役割:", "").strip()
        elif line.startswith("概要:"):
            current["summary"] = line.replace("概要:", "").strip()
    if "title" in current:
        sections.append(current)

    if sections:
        toc["sections"] = sections
        console.print(f"[green]✓ 編集後の目次を読み込みました（{len(sections)}章）[/green]")
    else:
        console.print("[yellow]⚠ 目次の読み込みに失敗しました。元の目次を使います。[/yellow]")

    return toc


# ──────────────────────────────────────────────────────────
# ステップ5〜9: 1本の特典を生成
# ──────────────────────────────────────────────────────────
def generate_one_report(candidate: dict, analysis: dict, inputs: dict, project_id: str):
    target = inputs["target"]
    safe_title = candidate["title"].replace("/", "_").replace("\\", "_")[:20]
    out_dir = OUTPUT_DIR / project_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- 目次生成 ----
    console.print(f"\n[bold cyan]目次を生成中: {candidate['title']}[/bold cyan]")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as p:
        p.add_task("目次を設計しています...")
        toc = generate_toc(candidate, analysis, target)

    issues = check_toc_validity(toc)
    if issues:
        console.print("[yellow]⚠ 目次に以下の問題があります:[/yellow]")
        for issue in issues:
            console.print(f"  - {issue}")

    console.print("\n[bold]【目次案】[/bold]")
    for s in toc.get("sections", []):
        console.print(f"  第{s['number']}章　{s['title']}　[dim]（{s.get('role','')}）[/dim]")
        console.print(f"         → {s.get('summary', '')}")

    # ---- 目次手動編集 ----
    if Confirm.ask("目次をテキストエディタで手動編集しますか？（編集不要ならNo）"):
        toc = _edit_toc_in_editor(toc, out_dir, console)
        # 編集後の目次を再表示
        console.print("\n[bold]【編集後の目次】[/bold]")
        for s in toc.get("sections", []):
            console.print(f"  第{s['number']}章　{s['title']}　[dim]（{s.get('role','')}）[/dim]")

    if not Confirm.ask("\nこの目次で本文生成を進めますか？"):
        console.print("[yellow]目次を確認して再度実行してください。[/yellow]")
        return None

    # ---- 本文 + ビジュアル生成 ----
    console.print("\n[bold cyan]本文・図解を生成中...[/bold cyan]")
    sections_data = []
    section_visuals = {}

    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
        task_greeting = progress.add_task("あいさつを生成中...", total=None)
        greeting = generate_greeting(candidate, target)
        progress.update(task_greeting, completed=True, description="[green]あいさつ ✓")

        task_intro = progress.add_task("はじめにを生成中...", total=None)
        intro = generate_intro(candidate, target)
        progress.update(task_intro, completed=True, description="[green]はじめに ✓")

        generated_texts = []
        for section in toc.get("sections", []):
            # 本文生成（文字数不足時は自動再試行）
            task_sec = progress.add_task(f"第{section['number']}章を生成中...", total=None)

            def _on_retry(attempt, current_len, sec=section):
                progress.update(
                    task_sec,
                    description=f"[yellow]第{sec['number']}章 再生成中 ({current_len}文字→{MIN_SECTION_CHARS}文字目標)[/yellow]"
                )

            text = generate_section(section, candidate, target, generated_texts, on_retry=_on_retry)
            generated_texts.append(text)
            sections_data.append({"number": section["number"], "title": section["title"], "text": text})
            progress.update(task_sec, completed=True, description=f"[green]第{section['number']}章 ✓ ({len(text)}文字)")

            # 図解生成
            task_vis = progress.add_task(f"第{section['number']}章 図解生成中...", total=None)
            visuals = generate_all_visuals_for_section(section, text, candidate, target, out_dir)
            section_visuals[section["number"]] = visuals
            vis_count = sum(1 for v in visuals if v.get("path"))
            progress.update(task_vis, completed=True,
                            description=f"[green]第{section['number']}章 図解 ✓ ({vis_count}点PNG)")

        task_conc = progress.add_task("おわりにを生成中...", total=None)
        conclusion = generate_conclusion(candidate, target, generated_texts)
        progress.update(task_conc, completed=True, description="[green]おわりに ✓")

        task_cover = progress.add_task("表紙素材を生成中...", total=None)
        cover_assets = generate_cover_assets(candidate, target)
        progress.update(task_cover, completed=True, description="[green]表紙 ✓")

    terms = generate_terms()

    # ---- 品質チェック ----
    console.print("\n[bold cyan]品質チェック中...[/bold cyan]")
    issues = run_all_checks(
        {**candidate, **cover_assets},
        sections_data,
    )
    if issues:
        console.print("[yellow]⚠ 品質上の注意点:[/yellow]")
        for issue in issues:
            console.print(f"  - {issue}")
    else:
        console.print("[green]✓ 品質チェック通過[/green]")

    # ---- Word出力 ----
    word_path = out_dir / f"{safe_title}.docx"
    console.print(f"\n[bold cyan]Word出力中: {word_path.name}[/bold cyan]")
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
    )
    console.print(f"[green]✓ Word出力完了: {word_path}[/green]")

    return {
        "candidate": candidate,
        "toc": toc,
        "cover_assets": cover_assets,
        "word_path": str(word_path),
        "quality_issues": issues,
        "section_visuals": {
            k: [{"title": v.get("title"), "type": v.get("type"), "ai_prompt": v.get("ai_prompt")} for v in vs]
            for k, vs in section_visuals.items()
        },
    }


# ──────────────────────────────────────────────────────────
# メインフロー
# ──────────────────────────────────────────────────────────
def main():
    console.print(Panel(
        "[bold green]特典量産システム v1.0[/bold green]\nローカルCLI版",
        expand=False
    ))

    # 既存案件を確認するか確認
    projects = list_projects()
    if projects and Confirm.ask(f"\n既存案件が{len(projects)}件あります。新しく始めますか？"):
        pass  # 新規作成へ
    elif projects and not Confirm.ask("\n新しく始めますか？"):
        console.print("既存案件からの再開は data/projects/ フォルダのJSONを参照してください。")
        sys.exit(0)

    # ---- 入力 ----
    inputs = collect_inputs()

    project_id = new_project_id()
    project_data = {"project_id": project_id, **inputs}

    # ---- 分析 ----
    analysis = step_analyze(inputs)
    project_data["analysis"] = analysis

    # ---- 候補生成 ----
    candidates_result = step_generate_candidates(inputs, analysis)
    project_data["candidates"] = candidates_result

    # ---- 候補選択 ----
    selected = step_select_candidates(candidates_result)
    project_data["selected_candidates"] = selected

    # ---- 途中保存 ----
    save_project(project_id, project_data)
    console.print(f"\n[dim]案件保存: data/projects/{project_id}.json[/dim]")

    # ---- 1本ずつ生成 ----
    results = []
    for i, candidate in enumerate(selected):
        console.print(Panel(
            f"[bold]{i+1}/{len(selected)}: {candidate['title']}[/bold]",
            title="生成開始",
            expand=False,
        ))
        result = generate_one_report(candidate, analysis, inputs, project_id)
        if result:
            results.append(result)

        if i < len(selected) - 1:
            if not Confirm.ask(f"\n次の特典（{selected[i+1]['title']}）を続けて生成しますか？"):
                console.print("[yellow]残りの生成をスキップしました。[/yellow]")
                break

    # ---- 最終保存 ----
    project_data["results"] = results
    save_project(project_id, project_data)

    # ---- 完了サマリ ----
    console.print(Panel(
        f"[bold green]完了！[/bold green]\n"
        f"生成本数: {len(results)}本\n"
        f"出力先: output/projects/{project_id}/",
        title="完了",
        expand=False,
    ))
    for r in results:
        console.print(f"  [green]✓[/green] {r['candidate']['title']} → {Path(r['word_path']).name}")


if __name__ == "__main__":
    main()
