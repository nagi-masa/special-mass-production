"""案件データの保存・読み込みモジュール"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from config import DATA_DIR


def new_project_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def save_project(project_id: str, data: dict):
    path = DATA_DIR / f"{project_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_project(project_id: str) -> dict:
    path = DATA_DIR / f"{project_id}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_projects() -> list[dict]:
    projects = []
    for p in sorted(DATA_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            projects.append({
                "id": p.stem,
                "product_name": data.get("product_name", ""),
                "target": data.get("target", ""),
                "created_at": data.get("created_at", ""),
                "candidates_count": len(data.get("candidates", {}).get("candidates", [])),
            })
        except Exception:
            pass
    return projects
