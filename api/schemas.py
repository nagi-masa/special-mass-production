"""Pydantic スキーマ定義"""
from pydantic import BaseModel


class MaterialInput(BaseModel):
    materials: list[str]
    product_name: str
    target: str
    notes: str = ""


class CandidateSelectInput(BaseModel):
    analysis: dict
    product_name: str
    target: str


class TocGenerateInput(BaseModel):
    candidate: dict
    analysis: dict
    target: str


class TocApproveInput(BaseModel):
    toc: dict  # 手動編集済みの場合もここで渡す


class GenerateReportInput(BaseModel):
    candidate: dict
    toc: dict
    analysis: dict
    target: str
    project_id: str
    author_name: str = ""
    copyright_text: str = ""
    author_profile: str = ""
    generate_visuals: bool = True
