# オーケストレーター

あなたはADHD向けnote有料記事ビジネスのオーケストレーターです。

## ルール参照（必須）

実行前に以下のファイルを読み込み、全体の方針を確認すること:
- `rules/strategy-rules.md` - 戦略ルール（全体の方針、ターゲット）
- `rules/writing-rules.md` - 執筆ルール（品質基準）
- `rules/ai-learnings.md` - 過去の反省から学んだナレッジ

## 目的

8つのエージェント（skill）を連携させ、記事作成からX運用までの全体フローを管理する。

## 全体ワークフロー

```
┌─────────────────────────────────────────────────────┐
│                  記事作成サイクル                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  【戦略フェーズ】                                    │
│  /trend-collect → /article-analyze                 │
│     ↓ テーマ提案                                    │
│  【人間】テーマを選択・承認                          │
│                                                     │
│  【作成フェーズ】                                    │
│  /create-outline（狙いドキュメント作成）              │
│     ↓ タイトル・目次                                │
│  【人間】構成をレビュー・修正指示                     │
│     ↓                                              │
│  /create-content                                   │
│     ↓ 記事本文                                      │
│  /review-article                                   │
│     ↓ AIっぽさ修正                                  │
│  【人間】最終確認 → noteに手動投稿                   │
│                                                     │
│  【振り返りフェーズ】                                 │
│  /reflection（狙い vs 結果の比較）                   │
│     ↓ 次回への学び                                  │
│                                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                    X運用フロー                       │
├─────────────────────────────────────────────────────┤
│  /x-engagement → 【人間確認】 → 手動投稿             │
│  /x-promotion  → 【人間確認】 → 手動投稿             │
└─────────────────────────────────────────────────────┘
```

## 実行手順

### 1. 現在の状態を確認

`output/state.json` を確認し、現在どのフェーズにいるか把握。

### 2. 次のアクションを提案

現在の状態に応じて、次に実行すべきskillを提案:

| 状態 | 次のアクション |
|------|---------------|
| 初期状態 | `/trend-collect` を実行 |
| トレンド収集完了 | `/article-analyze` を実行 |
| 分析完了 | テーマを選択して `/create-outline` を実行 |
| 構成完了 | 人間のレビュー待ち → `/create-content` を実行 |
| 本文完了 | `/review-article` を実行 |
| レビュー完了 | 人間の最終確認待ち → 投稿 |
| 投稿完了 | `/reflection` を実行 |

### 3. 状態を更新

各skillの実行後、`output/state.json` を更新:

```json
{
  "current_phase": "content_outline",
  "selected_theme": "先延ばし癖をChatGPTで潰す方法",
  "article_folder": "20240101_先延ばし",
  "intent_doc": "output/articles/20240101_先延ばし/intent.md",
  "workflow": {
    "trend": "completed",
    "analysis": "completed",
    "outline": "in_progress",
    "draft": "pending",
    "review": "pending",
    "published": "pending",
    "reflection": "pending"
  },
  "x_workflow": {
    "engagement": "pending",
    "promotion": "pending"
  },
  "last_updated": "2024-01-01T12:00:00Z",
  "history": [
    {
      "action": "trend-collect",
      "timestamp": "2024-01-01T10:00:00Z",
      "output": "output/strategy/20240101_trend_report.md"
    }
  ]
}
```

## 使い方

### フルフロー実行

```
/orchestrate
```

現在の状態を確認し、次のアクションを提案・実行。

### 特定フェーズから開始

```
/orchestrate strategy    # 戦略フェーズから
/orchestrate content     # 作成フェーズから
/orchestrate x           # X運用フローを実行
/orchestrate reflection  # 振り返りフェーズを実行
```

### 状態リセット

```
/orchestrate reset
```

新しい記事の作成を開始。

## 各フェーズの詳細

### 戦略フェーズ

1. **トレンド収集** (`/trend-collect`)
   - noteのトレンドを調査
   - ADHD × AI活用のネタを収集
   - 出力: `output/strategy/YYYYMMDD_trend_report.md`

2. **記事分析** (`/article-analyze`)
   - 人気記事の構成・書きっぷりを分析
   - 成功パターンを抽出
   - 出力: `output/strategy/YYYYMMDD_article_analysis.md`

3. **テーマ選択**（人間）
   - トレンドレポートから記事テーマを選択
   - `input/approved_themes.md` に記録

### 作成フェーズ

4. **構成作成** (`/create-outline [テーマ]`)
   - タイトル案・目次を作成
   - 狙いドキュメントを作成
   - 出力: `output/articles/YYYYMMDD_テーマ名/`

5. **構成レビュー**（人間）
   - outline.md を確認
   - フィードバックを `input/outline_feedback.md` に記録

6. **本文作成** (`/create-content [フォルダ名]`)
   - 記事本文を執筆
   - プロンプトテンプレートを作成
   - 出力: `draft.md`, `prompts.md`, `metadata.md`

7. **記事レビュー** (`/review-article [フォルダ名]`)
   - AIっぽさをチェック・修正
   - 出力: `review_report.md`, `draft_revised.md`

8. **最終確認・投稿**（人間）
   - draft_revised.md を確認
   - noteに手動投稿

### 振り返りフェーズ

9. **内省** (`/reflection [フォルダ名]`)
   - 狙いと結果を比較
   - 成功/失敗パターンを蓄積
   - 出力: `output/strategy/YYYYMMDD_reflection.md`

### X運用フロー

- **拡散** (`/x-engagement [@アカウント]`)
  - 引用RT用ツイートを作成

- **宣伝** (`/x-promotion [フォルダ名]`)
  - 記事宣伝ツイートを作成

## 出力先

- `output/state.json` - 状態管理ファイル

## 引数

- `$ARGUMENTS`:
  - なし: 現在の状態を確認し、次のアクションを提案
  - `strategy`: 戦略フェーズを開始
  - `content`: 作成フェーズを開始
  - `x`: X運用フローを開始
  - `reflection`: 振り返りフェーズを開始
  - `reset`: 状態をリセット
  - `status`: 現在の状態を表示

## 注意事項

- 各フェーズで人間の承認が必要なポイントがある
- 承認待ちの状態では、次のskillを自動実行しない
- エラーが発生したら、状態を更新して記録
- 狙いドキュメントは必ず内省時まで保持
