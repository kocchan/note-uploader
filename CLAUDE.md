# ADHD向けnote有料記事ビジネス

このプロジェクトは、ADHD当事者向けのAI活用術をテーマにしたnote有料記事ビジネスを運営するためのものです。

## プロジェクト概要

- **ターゲット**: 大人のADHD当事者（診断済み or グレーゾーン）
- **コンテンツ**: ADHD × AI活用術の有料記事（1,980円）
- **プラットフォーム**: note
- **プロモーション**: X（旧Twitter）

## ルール参照（必須）

**すべての作業を開始する前に、以下のルールファイルを読み込むこと:**

```
rules/
├── README.md           # ルールの使い方
├── strategy-rules.md   # 戦略ルール（人間が記載）
├── writing-rules.md    # 執筆ルール（人間が記載）
└── ai-learnings.md     # AI学習ログ（/reflection で追記）
```

これらのルールに従って作業を進めること。

## 利用可能なサブエージェント

| エージェント | 役割 | 呼び出し例 |
|-------------|------|-----------|
| `note-business` | ビジネス全体を統括 | 「記事を書きたい」「状況を教えて」 |
| `strategy-planner` | 戦略立案・テーマ提案 | 「次のネタを考えて」「競合を分析して」 |
| `note-writer` | 記事作成の全工程 | 「構成を作って」「本文を書いて」 |
| `x-manager` | X運用・プロモーション | 「宣伝ツイートを作って」 |

サブエージェントは `.claude/agents/` に定義されています。

## 利用可能なスキル

| スキル | 用途 | フェーズ |
|--------|------|----------|
| `/trend-collect` | トレンド収集・記事ネタ発掘 | 戦略 |
| `/article-analyze` | 人気記事の分析 | 戦略 |
| `/create-outline` | タイトル・構成・狙いドキュメント作成 | 作成 |
| `/create-content` | 記事本文の執筆 | 作成 |
| `/review-article` | AIっぽさチェック・修正 | 作成 |
| `/reflection` | 公開後の振り返り・学習 | 振り返り |
| `/x-engagement` | 引用RT用ツイート作成 | X運用 |
| `/x-promotion` | 記事宣伝ツイート作成 | X運用 |
| `/x-post` | X APIでツイート自動投稿（人間承認後） | X運用 |
| `/orchestrate` | 全体ワークフロー管理 | 管理 |

## 標準ワークフロー

```
【戦略フェーズ】
  /trend-collect → /article-analyze
     ↓ テーマ提案
  【人間】テーマを選択・承認

【作成フェーズ】
  /create-outline（狙いドキュメント作成）
     ↓ タイトル・目次
  【人間】構成をレビュー
     ↓
  /create-content
     ↓ 記事本文
  /review-article
     ↓ AIっぽさ修正
  【人間】最終確認 → noteに手動投稿

【振り返りフェーズ】
  /reflection（狙い vs 結果の比較）
     ↓ 学習を rules/ai-learnings.md に追記
```

## フォルダ構成

```
312_note/
├── CLAUDE.md                    # このファイル
├── rules/                       # ルール・ナレッジベース
├── output/
│   ├── strategy/                # トレンドレポート・分析・振り返り
│   ├── articles/                # 記事ごとのフォルダ
│   │   └── YYYYMMDD_テーマ名/
│   │       ├── intent.md        # 狙いドキュメント
│   │       ├── outline.md       # 構成案
│   │       ├── draft.md         # 記事本文
│   │       ├── draft_revised.md # 修正済み本文
│   │       └── prompts.md       # プロンプト集
│   └── x_posts/                 # ツイート案
└── .claude/skills/              # スキル定義
```

## コマンド例

```bash
# 新しい記事の作成を開始
/orchestrate

# トレンドを収集
/trend-collect

# 特定テーマで構成作成
/create-outline 先延ばし癖をChatGPTで潰す

# 記事の振り返り
/reflection 20260425_先延ばし攻略

# X投稿（人間承認後に自動投稿）
/x-promotion 20260425_先延ばし攻略  # ツイート案作成
/x-post "承認されたツイート本文"     # X APIで投稿
/x-post promotion                   # 最新の宣伝ツイートを投稿
```

## 注意事項

- 各フェーズで人間の承認が必要なポイントがある
- rulesフォルダのルールに必ず従う
- 狙いドキュメント（intent.md）は振り返りまで保持
- AIっぽい文章を避け、当事者目線で書く
