# 引継書 - 特典量産システム
更新日: 2026-04-13

---

## プロジェクト概要

**システム名:** 特典量産システム  
**目的:** 素材テキスト（ブログ・文字起こし・メモ等）からセミナー・LINE登録・個別相談用の特典レポート（Word形式＋図解PNG）を自動量産する  
**GitHubリポジトリ:** https://github.com/nagi-masa/special-mass-production  
**Streamlit Cloud URL:** https://special-mass-appuction-qmummsgckhinycstejsf2v.streamlit.app/  
**スキルファイル:** `C:\Users\touro\.claude\skills\special_mass_production\`

---

## 使用技術

| 項目 | 内容 |
|------|------|
| 言語 | Python |
| フロントエンド | Streamlit (`web/app.py`) |
| バックエンド | FastAPI (`api/main.py`) |
| Word出力 | python-docx |
| 図解生成 | matplotlib（日本語テキスト入りPNG） |
| AIプロバイダー | Gemini（デフォルト）/ Claude / OpenAI 切替可 |
| デフォルトモデル | gemini-2.5-flash |

---

## ディレクトリ構成

```
特典量産/
├── main.py                    # CLIエントリーポイント
├── config.py                  # 設定・品質基準値
├── requirements.txt
├── HANDOVER.md                # 本ファイル
├── TODO.md                    # タスク管理
├── README.md
├── core/
│   ├── claude_client.py       # AI API共通クライアント（Anthropic/OpenAI/Gemini対応）
│   ├── analyzer.py            # 素材分析
│   ├── candidate_generator.py # 特典候補生成
│   ├── toc_generator.py       # 目次生成
│   ├── content_generator.py   # 本文生成（文字数不足・途切れ時の自動再生成つき）
│   ├── quality_checker.py     # 品質チェック（文字数・タイトル長・途切れ検知）
│   ├── cover_generator.py     # 表紙素材生成
│   ├── visuals_generator.py   # 図解PNG生成（matplotlib）+ AIプロンプト出力
│   ├── word_exporter.py       # Word出力（図解挿入・フッター・表紙指示書つき）
│   └── project_store.py       # 案件JSON保存・読み込み
├── prompts/
│   ├── analyze_material.md
│   ├── generate_candidates.md
│   ├── generate_toc.md
│   ├── generate_section.md    # 本文生成プロンプト
│   ├── generate_cover.md      # 表紙デザイン生成プロンプト
│   └── generate_visuals.md    # 図解仕様生成プロンプト
├── api/
│   ├── main.py                # FastAPI バックエンド
│   └── schemas.py
├── web/
│   └── app.py                 # Streamlit フロントエンド
├── data/projects/             # 案件JSONデータ（自動生成）
└── output/projects/           # Word + PNG出力先（自動生成）
```

---

## 今セッションで行った修正（2026-04-13）

### ① 表紙デザイン指示書の構造化

**問題:** 表紙デザインメモが `design_concept` の1行テキスト垂れ流しで、実際の表紙制作に使えなかった。

**修正ファイル:**
- `prompts/generate_cover.md` — `subject`（被写体詳細）フィールドを追加。`color_scheme` の記述粒度を強化
- `core/cover_generator.py` — `subject` フィールドを結果dictに追加
- `core/word_exporter.py` — 表紙デザインメモを以下の構造化指示書に変更

**出力後の表紙指示書の構造:**
```
タイトル: / サブタイトル: / バッジ: / デザイン（カラー・被写体・サイズ）/
表紙文字サイズと比率（メイン60-80pt / サブ30-40pt / 著者18-24pt）/
デザインコンセプト / AI画像生成プロンプト
```

---

### ② 本文途切れ検知・自動再生成

**問題:** 本文テキストが途中で切れている箇所が複数あったが、文字数チェックだけでは検知できていなかった。

**修正ファイル:**
- `core/quality_checker.py` — `check_text_truncation()` を新設。文末が `。！？」』…` 以外で終わっていたら警告。`run_all_checks()` に組み込み
- `core/content_generator.py` — 再生成トリガーを「文字数不足 **OR** 途切れ検知」に拡張。再生成プロンプトに「必ず`。`で終わる完結した文章にすること」を追記

---

### ③ 図解品質改善

**問題:**
- 図解の品質が低く（質素・内容が薄い）、文字化けが発生していた
- `generate_visual_specs()` が章テキストを600文字しか渡していなかった
- プロンプトに最低生成数の強制・自己検証・デザイン仕様・日本語/英語の使い分けルールがなかった

**修正ファイル:**
- `prompts/generate_visuals.md` — 全面改訂。以下を追加：
  - 図解の出力方式（matplotlibで日本語テキスト入りPNG生成 vs AI画像プロンプト出力）を明確に分離
  - 最低2枚以上の強制ルール
  - Execution Flow（5ステップ）・Constraints・自己検証
  - デザイン仕様（ネイビー×ゴールド×ホワイト）
  - テキストは**すべて日本語**。英語は `type=image` の `ai_image_prompt` のみ
- `core/visuals_generator.py` — 章テキストの渡し量を600文字→**全文**に変更。枚数不足時の自動再生成（1回）を追加

**図解タイプと出力方式:**
| type | 出力 | テキスト |
|------|------|---------|
| key_points / steps / comparison / flowchart | matplotlibでPNG生成 | **日本語** |
| image | AI画像プロンプトのみ出力 | ai_image_promptのみ英語 |

---

### ④ スキルファイルの同期更新

**修正ファイル:** `C:\Users\touro\.claude\skills\special_mass_production\SKILL.md`
- STEP 5「表紙情報フォーマット」→ 構造化指示書に変更
- STEP 5「品質ルール」→ 文章途切れチェックを追加
- STEP 5.5「図解・イメージ設計」→ 最低2枚・日本語ルール・デザイン仕様・自己検証を追加
- JSONフォーマット → `cover_design` を `color_scheme` / `subject` / `design_concept` に分割

**修正ファイル:** `C:\Users\touro\.claude\skills\special_mass_production\word_writer.py`
- 表紙デザインメモ → 構造化指示書に変更（旧 `cover_design` フィールドとの後方互換あり）

---

## 未対応タスク（TODO.mdより）

| 項目 | 優先度 |
|------|--------|
| トーンの一貫性チェック（AI判定） | 中 |
| 図解カラーテーマを config.py から変更できるように | 低 |
| Markdown出力オプション | 低 |
| 表紙画像をWordへ差し込む（画像生成後） | 中 |
| サンプル案件で通しテスト | **高** |
| エラー時のわかりやすい案内 | 中 |
| 運用手順書 | 中 |
| 未作成候補一覧（再実行時） | 低 |
| 案件履歴画面（過去の生成一覧・再DL） | 低 |

---

## 次プロジェクト計画: Kindle出版量産システム

**方針:** 本システム（特典量産）をベースに、Kindle本の量産に対応した派生版を作る。

**詳細は別途 KINDLE_PLAN.md を作成予定。**

---

## 注意事項

- APIキーは `.env` ファイルで管理。Streamlit Cloud では Secrets に設定済み
- デフォルトプロバイダーは Gemini（`config.py` の `PROVIDER` で変更可）
- `data/projects/` と `output/projects/` はGitignore対象（案件データは共有しない）
