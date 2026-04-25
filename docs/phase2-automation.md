# Phase 2: 自動化アーキテクチャ設計

## 概要

GitHub Actions + Claude Code CLI + Slack MCP + Cloudflare Workers を使って、**エージェントが自律的に動作**し、人間レビューをSlack上で完結させる。

**特徴:**
- `.claude/agents/` のエージェント定義をそのまま使用
- `.claude/skills/` のスキルを自動実行
- **Slack MCP** で Claude が直接 Slack を操作
- **Cloudflare Workers** で Slack → GitHub Actions の即時トリガー
- 人間への質問は Slack 経由で非同期処理
- **パブリックリポジトリで GitHub Actions 無制限・無料**
- AWS不要、サーバーレスで完結

---

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                         Slack                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ #note-business チャンネル                                  │  │
│  │                                                           │  │
│  │ 【即時トリガー】                                           │  │
│  │ ・@note-bot ツイートして → 即座に GitHub Actions 起動     │  │
│  │ ・✅ リアクション追加 → 即座に投稿実行                     │  │
│  │                                                           │  │
│  │ 【定期実行】                                               │  │
│  │ ・毎日 12:00 ツイート提案が届く                            │  │
│  │ ・毎日 8:00 テーマ提案が届く                               │  │
│  └───────────────────────────┬───────────────────────────────┘  │
└───────────────────────────────┼─────────────────────────────────┘
                                │ Slack Events API
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Cloudflare Workers（無料）                       │
│                                                                  │
│  Slack からの Event を受信:                                      │
│  ・メンション (@note-bot)                                        │
│  ・リアクション追加 (✅ ❌ ✏️)                                    │
│  ・メッセージ投稿                                                │
│                    │                                             │
│                    ▼                                             │
│  GitHub repository_dispatch API を呼び出し                       │
│  → GitHub Actions を即時起動                                     │
└────────────────────┼────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions                                │
│                                                                  │
│  【トリガー】                                                    │
│  ・repository_dispatch: slack-command（即時）                    │
│  ・repository_dispatch: slack-reaction（即時）                   │
│  ・schedule: cron（定期実行）                                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Claude Code CLI + Slack MCP                   │  │
│  │                                                            │  │
│  │  claude -p "タスク内容" \                                   │  │
│  │         --mcp-config mcp.json \                            │  │
│  │         --dangerously-skip-permissions                     │  │
│  │                                                            │  │
│  │  Slack MCP Tools:                                          │  │
│  │  ・slack_list_channels    - チャンネル一覧                  │  │
│  │  ・slack_post_message     - メッセージ投稿                  │  │
│  │  ・slack_reply_to_thread  - スレッド返信                    │  │
│  │  ・slack_add_reaction     - リアクション追加                │  │
│  │  ・slack_get_channel_history - 履歴取得                    │  │
│  │  ・slack_get_thread_replies  - スレッド取得                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│      ┌────────────────────┼────────────────────┐                │
│      ▼                    ▼                    ▼                │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────┐         │
│  │ .claude/    │  │ rules/          │  │ X API       │         │
│  │ agents/     │  │                 │  │ (tweepy)    │         │
│  │ x-manager   │  │ x-posting-      │  │             │         │
│  │ note-writer │  │ rules.md        │  │ ツイート    │         │
│  │ ...         │  │ strategy-       │  │ 投稿        │         │
│  │             │  │ rules.md        │  │             │         │
│  └─────────────┘  └─────────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Slack MCP の仕組み

**MCP (Model Context Protocol)** を使うことで、Claude Code CLI が直接 Slack を操作できる。

### 利用可能な Slack MCP ツール

| ツール | 説明 |
|--------|------|
| `slack_list_channels` | チャンネル一覧を取得 |
| `slack_post_message` | チャンネルにメッセージを投稿 |
| `slack_reply_to_thread` | スレッドに返信 |
| `slack_add_reaction` | メッセージにリアクション追加 |
| `slack_get_channel_history` | チャンネルの履歴を取得 |
| `slack_get_thread_replies` | スレッドの返信を取得 |
| `slack_get_users` | ユーザー一覧を取得 |
| `slack_search_messages` | メッセージを検索 |

### メリット

1. **Python コード不要**: slack-sdk のスクリプトが不要に
2. **柔軟性**: Claude が状況に応じて適切な Slack 操作を選択
3. **統合**: エージェント定義内で自然に Slack 操作を指示できる

---

## 即時トリガーの仕組み

Cloudflare Workers が Slack Events を受信し、GitHub Actions を即座に起動。

```
┌────────────────────────────────────────────────────────────┐
│ 1. Slack でアクション発生                                   │
│    ・ユーザーが @note-bot と入力                            │
│    ・ユーザーが ✅ リアクションを追加                        │
└──────────────────────┬─────────────────────────────────────┘
                       │ Slack Events API (即時)
                       ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Cloudflare Workers が受信                                │
│    ・Event type を判定                                      │
│    ・必要な情報を抽出                                       │
└──────────────────────┬─────────────────────────────────────┘
                       │ HTTP POST (即時)
                       ▼
┌────────────────────────────────────────────────────────────┐
│ 3. GitHub repository_dispatch API                          │
│    POST /repos/{owner}/{repo}/dispatches                   │
│    {                                                       │
│      "event_type": "slack-reaction",                       │
│      "client_payload": {                                   │
│        "channel": "C0B0P1C07UY",                          │
│        "message_ts": "1234567890.123456",                  │
│        "reaction": "white_check_mark",                     │
│        "user": "U12345678"                                 │
│      }                                                     │
│    }                                                       │
└──────────────────────┬─────────────────────────────────────┘
                       │ (即時)
                       ▼
┌────────────────────────────────────────────────────────────┐
│ 4. GitHub Actions が起動                                    │
│    on:                                                     │
│      repository_dispatch:                                  │
│        types: [slack-reaction]                             │
└────────────────────────────────────────────────────────────┘
```

**遅延**: Slack アクション → GitHub Actions 起動まで **約1-3秒**

---

## エージェント構成

### 使用するエージェント

| エージェント | ファイル | 役割 |
|-------------|---------|------|
| X運用エージェント | `.claude/agents/x-manager.md` | ツイート作成・投稿管理 |
| 戦略プランナー | `.claude/agents/strategy-planner.md` | テーマ提案・競合分析 |
| 記事ライター | `.claude/agents/note-writer.md` | 記事作成 |
| ビジネス統括 | `.claude/agents/note-business.md` | 全体管理 |

### Slack MCP で不要になるスキル

| 旧スキル | 代替 |
|---------|------|
| `/slack-ask` | Slack MCP の `slack_post_message` + `slack_add_reaction` |

### 引き続き使用するスキル

| スキル | 用途 |
|--------|------|
| `/x-post` | X (Twitter) に投稿 |
| `/x-promotion` | 記事宣伝ツイート作成 |
| `/x-engagement` | 引用RT作成 |
| `/trend-collect` | トレンド収集 |
| `/reflection` | 振り返り・学習 |

---

## ディレクトリ構成

```
312_note/
├── .claude/
│   ├── agents/
│   │   ├── x-manager.md          # X運用エージェント
│   │   ├── strategy-planner.md   # 戦略プランナー
│   │   ├── note-writer.md        # 記事ライター
│   │   └── note-business.md      # ビジネス統括
│   └── skills/
│       ├── x-post/               # X投稿スキル
│       ├── x-promotion/          # 記事宣伝スキル
│       └── ...
├── .github/
│   └── workflows/
│       ├── slack-command.yml     # Slack コマンド処理（即時）
│       ├── slack-reaction.yml    # Slack リアクション処理（即時）
│       ├── daily-xpost.yml       # 毎日12:00: ツイート提案
│       ├── daily-trend.yml       # 毎日8:00: テーマ提案
│       └── weekly-reflection.yml # 毎週月曜: 振り返り
├── cloudflare/
│   └── slack-webhook-worker.js   # Cloudflare Workers スクリプト
├── mcp.json                      # MCP 設定ファイル
├── rules/
│   ├── x-posting-rules.md        # X投稿ルール
│   ├── strategy-rules.md         # 戦略ルール
│   └── ai-learnings.md           # AI学習ログ
└── output/
    └── x_posts/                  # 投稿履歴
```

---

## GitHub Actions ワークフロー

| ワークフロー | トリガー | 処理内容 |
|------------|---------|---------|
| `slack-command.yml` | repository_dispatch: slack-command | Slack コマンドを処理 |
| `slack-reaction.yml` | repository_dispatch: slack-reaction | リアクションを処理→投稿実行 |
| `daily-xpost.yml` | 毎日 12:00 JST | ツイート提案を Slack に投稿 |
| `daily-trend.yml` | 毎日 8:00 JST | テーマ提案を Slack に投稿 |
| `weekly-reflection.yml` | 毎週月曜 9:00 JST | 振り返りレポートを生成 |

---

## 必要な設定

### 1. GitHub Secrets

リポジトリの Settings → Secrets and variables → Actions で設定:

```
ANTHROPIC_API_KEY    # Claude API キー
SLACK_BOT_TOKEN      # Slack Bot Token (xoxb-xxx)
SLACK_TEAM_ID        # Slack Team ID (T0xxx)
SLACK_CHANNEL        # 投稿先チャンネルID (C0B0P1C07UY)
GITHUB_PAT           # GitHub Personal Access Token（repository_dispatch用）
X_API_KEY            # X API キー
X_API_KEY_SECRET     # X API シークレット
X_ACCESS_TOKEN       # X アクセストークン
X_ACCESS_TOKEN_SECRET # X アクセストークンシークレット
```

### 2. Cloudflare Workers 設定

Cloudflare Workers に以下の環境変数を設定:

```
GITHUB_PAT           # GitHub Personal Access Token
GITHUB_REPO          # リポジトリ名 (kocchan/note-uploader)
SLACK_SIGNING_SECRET # Slack App の Signing Secret
```

### 3. Slack App 設定

#### Event Subscriptions

1. https://api.slack.com/apps → アプリを選択
2. **Event Subscriptions** → Enable Events: **On**
3. **Request URL**: Cloudflare Workers の URL を設定
   ```
   https://your-worker.your-subdomain.workers.dev/slack/events
   ```
4. **Subscribe to bot events** で以下を追加:
   - `app_mention` - メンション検知
   - `reaction_added` - リアクション追加検知
   - `message.channels` - チャンネルメッセージ検知

#### Bot Token Scopes

```
app_mentions:read   # メンション読み取り
channels:history    # チャンネル履歴読み取り
channels:read       # チャンネル一覧取得
chat:write          # メッセージ送信
reactions:read      # リアクション読み取り
reactions:write     # リアクション追加
users:read          # ユーザー情報取得
```

---

## 自動化フロー

### フロー1: 定期ツイート提案（毎日12:00）

```
[GitHub Actions: 毎日 12:00]
         │
         ▼
[Claude Code CLI + Slack MCP]
  1. rules/x-posting-rules.md を読む
  2. output/articles/ を確認
  3. ツイート案を2-3個作成
  4. Slack MCP でメッセージ投稿
  5. Slack MCP でリアクション追加 (✅ ❌ ✏️)
         │
         ▼
┌─────────────────────────────────────┐
│ Slack: #note-business               │
│ 🐦 本日のツイート提案                │
│ 【案1】ADHDの「あとでやる」は...    │
│ ✅ ❌ ✏️                             │
└─────────────────────────────────────┘
```

### フロー2: 即時リアクション処理

```
┌─────────────────────────────────────┐
│ Slack: 人間が ✅ をクリック          │
└──────────────────┬──────────────────┘
                   │ (即時)
                   ▼
[Cloudflare Workers]
  Slack Event を受信
  → GitHub repository_dispatch
                   │ (約1-3秒)
                   ▼
[GitHub Actions: slack-reaction.yml]
                   │
                   ▼
[Claude Code CLI + Slack MCP]
  1. Event payload からメッセージを特定
  2. Slack MCP でスレッド内容を取得
  3. 承認されたツイートを抽出
  4. /x-post でXに投稿
  5. Slack MCP でスレッドに「✅ 投稿完了」と返信
```

### フロー3: Slack コマンド処理

```
┌─────────────────────────────────────┐
│ Slack: @note-bot 今日のツイート作って │
└──────────────────┬──────────────────┘
                   │ (即時)
                   ▼
[Cloudflare Workers]
  app_mention Event を受信
  → GitHub repository_dispatch
                   │ (約1-3秒)
                   ▼
[GitHub Actions: slack-command.yml]
                   │
                   ▼
[Claude Code CLI + Slack MCP]
  1. Event payload からメッセージを取得
  2. コマンド内容を解析
  3. 適切なエージェント/スキルを実行
  4. Slack MCP で結果を返信
```

---

## 技術スタック

| コンポーネント | 技術 | 備考 |
|--------------|------|------|
| 定期スケジューラー | GitHub Actions | cron式で定期実行 |
| 即時トリガー | Cloudflare Workers | Slack → GitHub Actions |
| エージェント実行 | Claude Code CLI | MCP 経由で Slack 操作 |
| Slack 連携 | Slack MCP | @modelcontextprotocol/server-slack |
| エージェント定義 | `.claude/agents/*.md` | 既存のエージェントをそのまま使用 |
| スキル | `.claude/skills/*/SKILL.md` | 既存のスキルをそのまま使用 |
| X投稿 | tweepy (X API v2) | 既存の /x-post スキル |
| 状態管理 | リポジトリ内ファイル | output/に保存 |

---

## 実装ステップ

### Step 1: MCP 設定 ⏳
- [ ] mcp.json ファイル作成
- [ ] Slack Team ID 取得
- [ ] GitHub Actions で MCP 設定

### Step 2: Cloudflare Workers 設定 ⏳
- [ ] Cloudflare アカウント作成（無料）
- [ ] Workers スクリプト作成・デプロイ
- [ ] 環境変数設定
- [ ] Slack App の Request URL 設定

### Step 3: Slack App 更新 ⏳
- [ ] Event Subscriptions 有効化
- [ ] Bot Token Scopes 追加
- [ ] Request URL 設定・検証

### Step 4: GitHub Actions 更新 ⏳
- [ ] slack-command.yml 作成
- [ ] slack-reaction.yml 作成
- [ ] 既存ワークフローを MCP 対応に更新

### Step 5: テスト ⏳
- [ ] Slack メンションテスト
- [ ] リアクション検知テスト
- [ ] 定期実行テスト

---

## 費用

| サービス | 費用 |
|---------|------|
| GitHub Actions | **無料**（パブリックリポジトリ無制限） |
| Cloudflare Workers | **無料**（10万リクエスト/日まで） |
| Claude API | ~$5-15/月（Claude Code CLI 経由） |
| X API | ~$0.10/月（10投稿 × $0.01） |
| **合計** | **~$5-16/月** |

---

## メリット

1. **即時性**: Slack アクションから1-3秒で GitHub Actions 起動
2. **低コスト**: すべて無料枠内で運用可能
3. **シンプル**: Slack MCP で Python コード不要
4. **柔軟性**: Claude が状況に応じて適切に判断
5. **エージェント活用**: ローカルで作成したエージェントをそのまま使用
6. **サーバーレス**: AWS 不要、Cloudflare Workers + GitHub Actions で完結

## 制限事項

1. **Cloudflare Workers の制限**: CPU 時間 10ms（無料プラン）、ただし webhook 転送には十分
2. **GitHub Actions の実行時間**: 最大6時間/ジョブ
3. **Slack Events API**: 3秒以内にレスポンスが必要（Workers で即時応答）

---

## 次のアクション

1. **mcp.json 作成**
2. **Cloudflare Workers デプロイ**
3. **Slack App 設定更新**
4. **GitHub Actions 更新**
5. **テスト実行**
