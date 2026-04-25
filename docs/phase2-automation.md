# Phase 2: 自動化アーキテクチャ設計

## 概要

GitHub Actions + Slack Bolt を使って、エージェントが自律的に動作し、人間レビューをSlack上で完結させる。

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Actions (Scheduler)                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ 毎日 8:00    │ │ 毎週月曜     │ │ Slack Webhook トリガー   │ │
│  │ トレンド収集 │ │ 振り返り     │ │ オンデマンド実行         │ │
│  └──────┬───────┘ └──────┬───────┘ └────────────┬─────────────┘ │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude API / Claude Code                     │
│                                                                 │
│  スキル実行 → 成果物生成 → レビュー依頼をSlackに送信            │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Slack Bolt App (常駐)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ #note-business チャンネル                                │   │
│  │                                                         │   │
│  │ 🤖 Bot: 新しい記事テーマを提案します                      │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ テーマ: Claude × ADHD仕事術                         │ │   │
│  │ │ 理由: トレンド分析の結果...                          │ │   │
│  │ │                                                     │ │   │
│  │ │ [✅ 承認] [✏️ 修正] [❌ 却下]                        │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  承認 → GitHub Actions トリガー → 次のステップ実行             │
└─────────────────────────────────────────────────────────────────┘
```

## コンポーネント

### 1. GitHub Actions ワークフロー

```
.github/workflows/
├── daily-trend.yml        # 毎日: トレンド収集 → テーマ提案
├── daily-x-post.yml       # 毎日: X投稿提案
├── weekly-reflection.yml  # 毎週: 振り返り → 戦略更新
├── on-review-approved.yml # Slack承認時: 次ステップ実行
└── manual-trigger.yml     # 手動実行用
```

### 2. Slack Bolt App

```
src/slack/
├── app.py                 # メインアプリ
├── handlers/
│   ├── review_handlers.py # ボタン押下時の処理
│   ├── commands.py        # スラッシュコマンド
│   └── modals.py          # 修正用モーダル
├── messages/
│   ├── templates.py       # メッセージテンプレート
│   └── blocks.py          # Slack Block Kit
└── utils/
    ├── github_trigger.py  # GitHub Actions トリガー
    └── state.py           # 状態管理
```

### 3. Claude 実行レイヤー

```
src/claude/
├── executor.py            # Claude API 呼び出し
├── skills/                # スキル実行ロジック
│   ├── trend_collect.py
│   ├── create_outline.py
│   ├── x_post.py
│   └── ...
└── prompts/               # プロンプトテンプレート
```

## 自動化フロー

### フロー1: 毎日のトレンド収集 → テーマ提案

```
[GitHub Actions: 毎日 8:00]
     │
     ▼
[Claude: /trend-collect 実行]
     │
     ▼
[トレンドレポート生成]
     │
     ▼
[Claude: テーマ3つ提案]
     │
     ▼
[Slack: テーマ選択メッセージ送信]
     │
     ├─ [ユーザーがテーマ選択]
     │        │
     │        ▼
     │   [GitHub Actions: /create-outline トリガー]
     │        │
     │        ▼
     │   [Slack: 構成レビュー依頼]
     │
     └─ [24時間反応なし]
              │
              ▼
         [リマインダー送信]
```

### フロー2: 記事作成 → 公開

```
[構成承認後]
     │
     ▼
[Claude: /create-content 実行]
     │
     ▼
[Claude: /review-article 実行]
     │
     ▼
[Slack: 最終レビュー依頼]
     │
     ├─ [承認] → [note投稿リンク生成 + 宣伝ツイート提案]
     └─ [修正依頼] → [修正後、再度レビュー依頼]
```

### フロー3: X運用自動化

```
[記事公開後 or 定期スケジュール]
     │
     ▼
[Claude: /x-promotion 実行]
     │
     ▼
[Slack: ツイート案レビュー依頼]
     │
     ├─ [承認] → [/x-post で自動投稿] → [結果をSlackに通知]
     └─ [修正] → [修正モーダル表示] → [修正後、再度確認]
```

## Slackメッセージ例

### テーマ提案

```
🎯 新しい記事テーマを提案します

━━━━━━━━━━━━━━━━━━━━━━━━

**トレンド分析結果:**
• Claude 3.5 Sonnet × 業務効率化が急上昇
• 「先延ばし」関連の検索が継続的に高い

**提案テーマ:**

1️⃣ Claude × ADHD仕事術
   └ 需要: 高 | 競合: 少

2️⃣ AI習慣化コーチ
   └ 需要: 中 | 競合: 中

3️⃣ タスク管理プロンプト集
   └ 需要: 高 | 競合: 多

━━━━━━━━━━━━━━━━━━━━━━━━

[1️⃣ を選択] [2️⃣ を選択] [3️⃣ を選択] [🔄 別の提案]
```

### ツイートレビュー

```
🐦 ツイート投稿の確認

━━━━━━━━━━━━━━━━━━━━━━━━

**投稿内容:**
```
ADHDの「あとでやる」は永遠に来ない...😇

だからChatGPTに外注することにした!

具体的なプロンプト5つをnoteにまとめました👍
https://note.com/xxx
```

**文字数:** 89文字 ✅

━━━━━━━━━━━━━━━━━━━━━━━━

[✅ このまま投稿] [✏️ 修正する] [❌ キャンセル]
```

## 技術スタック

| コンポーネント | 技術 | 備考 |
|--------------|------|------|
| スケジューラー | GitHub Actions | cron式でスケジュール |
| Slack App | Slack Bolt (Python) | ソケットモード推奨 |
| ホスティング | Railway / Heroku / AWS Lambda | Slack App用 |
| AI実行 | Claude API (Anthropic SDK) | claude-3-5-sonnet |
| 状態管理 | GitHub リポジトリ内JSON | シンプルに |
| X投稿 | 既存の post_tweet.py | 流用 |

## 必要な設定

### 環境変数

```env
# Slack
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_APP_TOKEN=xapp-xxx  # ソケットモード用
SLACK_SIGNING_SECRET=xxx

# Claude
ANTHROPIC_API_KEY=sk-ant-xxx

# GitHub
GITHUB_TOKEN=ghp_xxx

# X (Twitter)
X_API_KEY=xxx
X_API_KEY_SECRET=xxx
X_ACCESS_TOKEN=xxx
X_ACCESS_TOKEN_SECRET=xxx
```

### Slack App 権限

```yaml
oauth_scopes:
  - chat:write
  - chat:write.public
  - commands
  - files:write
  - reactions:write

event_subscriptions:
  - message.channels
  - app_mention

interactivity:
  - shortcuts
  - interactive_messages
```

## 実装ステップ

### Step 1: Slack App 基盤 (1-2日)
- [ ] Slack App 作成 (api.slack.com)
- [ ] Slack Bolt セットアップ
- [ ] 基本的なメッセージ送信確認
- [ ] Railway/Herokuにデプロイ

### Step 2: レビューフロー (2-3日)
- [ ] 承認/却下ボタンのハンドラー
- [ ] 修正モーダルの実装
- [ ] GitHub Actions トリガー連携

### Step 3: Claude 統合 (2-3日)
- [ ] Claude API 呼び出しラッパー
- [ ] スキルをAPI版に移植
- [ ] 成果物 → Slackメッセージ変換

### Step 4: GitHub Actions (1-2日)
- [ ] 日次トレンド収集ワークフロー
- [ ] 週次振り返りワークフロー
- [ ] Slack承認 → 次ステップトリガー

### Step 5: 統合テスト (1-2日)
- [ ] エンドツーエンドテスト
- [ ] エラーハンドリング
- [ ] 本番運用開始

## 次のアクション

1. **Slack App 作成**: https://api.slack.com/apps で新規作成
2. **ソケットモード有効化**: 常時接続のため
3. **基本構造の実装開始**

---

## 質問事項

実装を始める前に確認:

1. **ホスティング先**: Railway / Heroku / Render / AWS のどれを使いますか？
2. **Slackワークスペース**: 既存のワークスペースを使いますか？新規作成？
3. **優先度**: まずどのフローから実装しますか？（トレンド収集 or X投稿 or 記事作成）
