"""
ビジュアル生成モジュール
- Claude APIでビジュアル仕様（JSON）を生成
- matplotlibで図解PNGをレンダリング（日本語テキスト入り）
- AIプロンプトも合わせて出力
"""
import json
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # GUIなし（サーバー / CLI用）
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

from core.claude_client import call_claude
from config import PROMPTS_DIR

# ── カラーパレット ──────────────────────────────────────
COLORS = {
    "primary":    "#2C5F8A",
    "accent":     "#E8A020",
    "bg":         "#F4F7FB",
    "bg2":        "#FFFFFF",
    "text":       "#2D3748",
    "subtext":    "#718096",
    "steps":      ["#4A90D9", "#5BA85C", "#E8A020", "#D05A5A", "#8B6BB1", "#3AAFA9"],
    "left_col":   "#FADBD8",
    "right_col":  "#D5F5E3",
    "left_title": "#C0392B",
    "right_title":"#27AE60",
}


# ── 日本語フォント設定 ────────────────────────────────────
def _setup_jp_font():
    """OSに応じて日本語フォントを設定する"""
    try:
        import japanize_matplotlib  # noqa: F401 (import だけで有効になる)
        return
    except ImportError:
        pass

    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}

    if platform.system() == "Windows":
        candidates = ["Yu Gothic", "MS Gothic", "Meiryo", "MS Mincho"]
    elif platform.system() == "Darwin":
        candidates = ["Hiragino Sans", "Hiragino Kaku Gothic Pro", "AppleGothic"]
    else:
        candidates = ["IPAexGothic", "IPAGothic", "TakaoGothic", "VL Gothic", "Noto Sans CJK JP"]

    for font in candidates:
        if font in available:
            matplotlib.rcParams["font.family"] = font
            return


_setup_jp_font()


# ── Claude でビジュアル仕様を生成 ────────────────────────
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


MIN_VISUALS_PER_SECTION = 2  # 1章あたりの最低図解枚数


def generate_visual_specs(section: dict, section_text: str, candidate: dict, target: str) -> list[dict]:
    """
    1章のテキストからビジュアル仕様リストを生成する。
    返り値: [{"type": ..., "title": ..., "content": {...}, ...}, ...]
    文字数不足・最低枚数未達の場合は再生成を1回行う。
    """
    system_prompt = load_prompt("generate_visuals.md")

    def _build_prompt(retry: bool = False) -> str:
        retry_note = ""
        if retry:
            retry_note = f"\n【重要】前回の生成で図解が{MIN_VISUALS_PER_SECTION}枚未満でした。必ず{MIN_VISUALS_PER_SECTION}枚以上の図解・イメージ画像を設計してください。\n"
        return f"""
# 章番号: 第{section["number"]}章
# 章タイトル: {section["title"]}
# ストーリー上の役割: {section.get("role", "")}
# ターゲット: {target}
# 特典タイトル: {candidate["title"]}
{retry_note}
# 章のテキスト（全文）:
{section_text}
"""

    for attempt in range(2):
        raw = call_claude(system_prompt, _build_prompt(retry=(attempt > 0)), max_tokens=3000)

        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            result = json.loads(raw[start:end])
            visuals = result.get("visuals", [])
        except (ValueError, json.JSONDecodeError):
            visuals = []

        if len(visuals) >= MIN_VISUALS_PER_SECTION:
            return visuals

        # 枚数不足 → 1回だけ再生成
        if attempt == 0:
            print(f"[visuals] 第{section['number']}章: 図解{len(visuals)}枚（最低{MIN_VISUALS_PER_SECTION}枚必要）→ 再生成")

    return visuals


# ── matplotlib レンダリング ───────────────────────────────
def _render_key_points(ax, title: str, points: list[str]):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # タイトルボックス
    title_box = FancyBboxPatch((0.3, 8.2), 9.4, 1.2,
                               boxstyle="round,pad=0.1",
                               facecolor=COLORS["primary"], edgecolor="none")
    ax.add_patch(title_box)
    ax.text(5, 8.8, title, ha="center", va="center",
            fontsize=13, fontweight="bold", color="white")

    # ポイントリスト
    max_points = min(len(points), 6)
    row_h = 7.5 / max_points if max_points > 0 else 1.5
    for i, pt in enumerate(points[:max_points]):
        y = 7.5 - i * row_h
        # 番号バッジ
        badge = plt.Circle((0.8, y), 0.35, color=COLORS["accent"], zorder=3)
        ax.add_patch(badge)
        ax.text(0.8, y, str(i + 1), ha="center", va="center",
                fontsize=10, fontweight="bold", color="white", zorder=4)
        # テキスト（長い場合は折り返し）
        wrapped = _wrap_text(pt, 28)
        ax.text(1.5, y, wrapped, ha="left", va="center",
                fontsize=10, color=COLORS["text"])

    ax.set_facecolor(COLORS["bg"])


def _render_steps(ax, title: str, steps: list[str]):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_facecolor(COLORS["bg"])

    # タイトル
    ax.text(5, 9.5, title, ha="center", va="top",
            fontsize=13, fontweight="bold", color=COLORS["primary"])

    n = min(len(steps), 6)
    if n == 0:
        return

    step_h = 7.5 / n
    for i, step in enumerate(steps[:n]):
        y_center = 8.5 - i * step_h - step_h / 2
        color = COLORS["steps"][i % len(COLORS["steps"])]

        box = FancyBboxPatch((0.5, y_center - 0.55), 9, 1.0,
                             boxstyle="round,pad=0.1",
                             facecolor=color, edgecolor="none", alpha=0.15)
        ax.add_patch(box)

        ax.text(1.2, y_center, f"STEP {i+1}", ha="left", va="center",
                fontsize=9, fontweight="bold", color=color)
        ax.text(2.8, y_center, _wrap_text(step, 30), ha="left", va="center",
                fontsize=10, color=COLORS["text"])

        # 矢印
        if i < n - 1:
            ax.annotate("", xy=(5, y_center - 0.6), xytext=(5, y_center - 0.5),
                        arrowprops=dict(arrowstyle="->", color=COLORS["subtext"], lw=1.5))


def _render_comparison(ax, title: str, left_label: str, right_label: str,
                       left_items: list[str], right_items: list[str]):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_facecolor(COLORS["bg2"])

    # タイトル
    ax.text(5, 9.5, title, ha="center", va="top",
            fontsize=13, fontweight="bold", color=COLORS["text"])

    # 左列（現状/問題）
    left_box = FancyBboxPatch((0.3, 0.5), 4.2, 8.0,
                              boxstyle="round,pad=0.1",
                              facecolor=COLORS["left_col"], edgecolor=COLORS["left_title"], lw=1.5)
    ax.add_patch(left_box)
    ax.text(2.4, 8.1, left_label, ha="center", va="center",
            fontsize=12, fontweight="bold", color=COLORS["left_title"])
    for i, item in enumerate(left_items[:5]):
        ax.text(0.7, 7.0 - i * 1.3, f"✗  {_wrap_text(item, 18)}",
                ha="left", va="center", fontsize=9, color=COLORS["left_title"])

    # 右列（理想/解決）
    right_box = FancyBboxPatch((5.5, 0.5), 4.2, 8.0,
                               boxstyle="round,pad=0.1",
                               facecolor=COLORS["right_col"], edgecolor=COLORS["right_title"], lw=1.5)
    ax.add_patch(right_box)
    ax.text(7.6, 8.1, right_label, ha="center", va="center",
            fontsize=12, fontweight="bold", color=COLORS["right_title"])
    for i, item in enumerate(right_items[:5]):
        ax.text(5.8, 7.0 - i * 1.3, f"✓  {_wrap_text(item, 18)}",
                ha="left", va="center", fontsize=9, color=COLORS["right_title"])

    # 中央矢印
    ax.annotate("", xy=(5.4, 5), xytext=(4.6, 5),
                arrowprops=dict(arrowstyle="->", color=COLORS["primary"], lw=2.5))


def _render_flowchart(ax, title: str, items: list[str]):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_facecolor(COLORS["bg"])

    ax.text(5, 9.5, title, ha="center", va="top",
            fontsize=13, fontweight="bold", color=COLORS["primary"])

    n = min(len(items), 5)
    if n == 0:
        return

    box_w = min(9.0 / n - 0.3, 2.5)
    total_w = n * box_w + (n - 1) * 0.4
    start_x = (10 - total_w) / 2

    for i, item in enumerate(items[:n]):
        x = start_x + i * (box_w + 0.4)
        cx = x + box_w / 2
        color = COLORS["steps"][i % len(COLORS["steps"])]

        box = FancyBboxPatch((x, 3.5), box_w, 2.5,
                             boxstyle="round,pad=0.1",
                             facecolor=color, edgecolor="none", alpha=0.85)
        ax.add_patch(box)

        wrapped = _wrap_text(item, int(box_w * 5))
        ax.text(cx, 4.75, wrapped, ha="center", va="center",
                fontsize=9, fontweight="bold", color="white",
                multialignment="center")

        # 矢印
        if i < n - 1:
            next_x = start_x + (i + 1) * (box_w + 0.4)
            ax.annotate("", xy=(next_x - 0.05, 4.75),
                        xytext=(x + box_w + 0.05, 4.75),
                        arrowprops=dict(arrowstyle="->", color=COLORS["primary"], lw=2))


def _wrap_text(text: str, max_len: int) -> str:
    """日本語を改行で折り返す"""
    if len(text) <= max_len:
        return text
    lines = []
    while len(text) > max_len:
        lines.append(text[:max_len])
        text = text[max_len:]
    lines.append(text)
    return "\n".join(lines)


# ── PNG生成 ──────────────────────────────────────────────
def render_visual_as_png(visual: dict, output_path: Path) -> Path | None:
    """
    ビジュアル仕様をmatplotlibでPNGとして保存する。
    type='image'はAIプロンプトのみなのでスキップ（None返し）。
    失敗した場合もNoneを返す。
    """
    vtype = visual.get("type", "")
    title = visual.get("title", "")
    content = visual.get("content", {})

    if vtype == "image":
        return None  # matplotlibでは描けない

    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor(COLORS["bg"])

        if vtype == "key_points":
            _render_key_points(ax, title, content.get("points", []))
        elif vtype == "steps":
            _render_steps(ax, title, content.get("steps", []))
        elif vtype == "comparison":
            _render_comparison(
                ax, title,
                content.get("left_label", "現状"),
                content.get("right_label", "理想"),
                content.get("left_items", []),
                content.get("right_items", []),
            )
        elif vtype == "flowchart":
            _render_flowchart(ax, title, content.get("items", []))
        else:
            plt.close()
            return None

        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150, bbox_inches="tight",
                    facecolor=COLORS["bg"])
        plt.close()
        return output_path

    except Exception as e:
        plt.close()
        print(f"[visuals] PNG生成失敗 ({vtype}): {e}")
        return None


# ── 全章まとめて生成 ─────────────────────────────────────
def generate_all_visuals_for_section(
    section: dict,
    section_text: str,
    candidate: dict,
    target: str,
    out_dir: Path,
) -> list[dict]:
    """
    1章分のビジュアルを生成してPNGを保存する。
    返り値: [{"path": Path | None, "caption": str, "ai_prompt": str, "type": str, "title": str}]
    """
    specs = generate_visual_specs(section, section_text, candidate, target)
    results = []

    for idx, spec in enumerate(specs):
        png_path = out_dir / f"visual_ch{section['number']}_{idx+1}.png"
        rendered = render_visual_as_png(spec, png_path)

        results.append({
            "path": rendered,           # PNG Path or None
            "caption": spec.get("caption", ""),
            "ai_prompt": spec.get("ai_image_prompt", ""),
            "type": spec.get("type", ""),
            "title": spec.get("title", ""),
            "position": spec.get("position", "after_text"),
        })

    return results
