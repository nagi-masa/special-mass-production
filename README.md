# 特典量産システム

素材（ブログ記事・文字起こし・アイデアメモ等）を入力すると、
特典レポート（Word形式 + 図解PNG付き）を自動生成するシステムです。

## セットアップ

### 1. Python環境

```bash
pip install -r requirements.txt
```

### 2. APIキーの設定

```bash
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定
```

---

## 3つの起動方法

### A) CLIで使う（ローカル完結・一番シンプル）

```bash
python main.py
```

### B) Webアプリで使う（ブラウザUI）

```bash
streamlit run web/app.py
```

### C) API として使う（外部連携・将来のフロント分離用）

```bash
uvicorn api.main:app --reload --port 8000
# ブラウザで http://localhost:8000/docs を開く
```

---

## フォルダ構成

```
特典量産/
├── main.py                   # CLIエントリーポイント
├── config.py                 # 設定・品質基準値
├── requirements.txt
├── sample_input.txt          # テスト用サンプル素材
├── TODO.md
├── core/
│   ├── claude_client.py      # Claude API共通
│   ├── analyzer.py           # 素材分析
│   ├── candidate_generator.py
│   ├── toc_generator.py
│   ├── content_generator.py  # 本文生成（文字数不足時の自動再試行つき）
│   ├── quality_checker.py
│   ├── cover_generator.py
│   ├── visuals_generator.py  # 図解PNG生成 + AIプロンプト出力
│   ├── word_exporter.py      # Word出力（図解挿入つき）
│   └── project_store.py
├── prompts/                  # ここを編集するだけで品質調整できる
│   ├── analyze_material.md
│   ├── generate_candidates.md
│   ├── generate_toc.md
│   ├── generate_section.md
│   ├── generate_cover.md
│   └── generate_visuals.md   # 図解仕様生成プロンプト
├── api/
│   ├── main.py               # FastAPI バックエンド
│   └── schemas.py
├── web/
│   └── app.py                # Streamlit フロントエンド
├── data/projects/            # 案件JSONデータ（自動生成）
└── output/projects/          # Word + PNG出力先（自動生成）
```

---

## 実行フロー

1. 商品名・ターゲット・補足メモを入力
2. 素材テキストを入力（最大3件）
3. Claude が素材を分析（テーマ・悩み・理想を抽出）
4. 特典候補を一覧表示（タイトル・サブタイトル・バッジ付き）
5. 作る特典を1〜5件選択
6. 各特典の目次を提案 → **テキストエディタで手動編集も可能**
7. 本文を章ごとに自動生成（文字数不足時は自動再試行）
8. 各章に図解・ステップ図・比較図をPNGで自動生成・挿入
9. Word ファイルとして出力（AI画像プロンプトも文書内に記載）

---

## 出力物

`output/projects/<案件ID>/` フォルダ：
- `<タイトル>.docx` — Word形式のレポート全文（図解PNG挿入済み）
- `visual_ch<章番号>_<番号>.png` — 各章の図解PNG
- `toc_edit.txt` — 目次編集ファイル（手動編集時）

---

## 図解の種類

| 種類 | 説明 |
|---|---|
| `key_points` | 重要ポイントをナンバリングした箇条書き図 |
| `steps` | 手順・プロセスのステップ図（3〜6ステップ） |
| `comparison` | ビフォーアフター / 問題vs解決策の比較図 |
| `flowchart` | 横並びフロー図（3〜5要素） |
| `image` | AI画像生成プロンプトのみ出力（Midjourney/DALL-E用） |

すべての図解テキストは日本語。

---

## プロンプト調整

`prompts/` フォルダのMarkdownファイルを編集することで、
コードを変えずに生成品質を調整できます。
特に `generate_visuals.md` を編集すると図解の傾向を変えられます。
