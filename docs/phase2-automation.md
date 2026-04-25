# Phase 2: 自動化アーキテクチャ設計

## 概要

GitHub Actions + Claude Code CLI + Slack を使って、**エージェントが自律的に動作**し、人間レビューをSlack上で完結させる。

**特徴:**
- `.claude/agents/` のエージェント定義をそのまま使用
- `.claude/skills/` のスキルを自動実行
- 人間への質問は Slack 経由で非同期処理
- **Slack Workflow Builder で即時トリガー**（リアクション→即実行）
- AWS不要、GitHub Actionsのみで完結

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Scheduler)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ 毎日 8:00    │ │ 毎日 12:00   │ │ 毎週月曜 9:00            │ │
│  │ テーマ提案   │ │ X投稿提案    │ │ 振り返り                 │ │
│  └──────┬───────┘ └──────┬───────┘ └────────────┬─────────────┘ │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code CLI                              │
│         （内部で ANTHROPIC_API_KEY を使って Claude API を呼ぶ）    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ claude -p "タスク内容" --dangerously-skip-permissions    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│      エージェント定義・ルール・スキルを自動で読み込み              │
│                           │                                     │
│          ┌────────────────┼────────────────┐                   │
│          ▼                ▼                ▼                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ .claude/    │  │ rules/      │  │ .claude/    │            │
│  │ agents/     │  │             │  │ skills/     │            │
│  │ x-manager   │  │ x-posting-  │  │ /slack-ask  │            │
│  │ note-writer │  │ rules.md    │  │ /x-post     │            │
│  │ ...         │  │ strategy-   │  │ /x-promotion│            │
│  │             │  │ rules.md    │  │ ...         │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼ /slack-ask スキルで投稿
┌─────────────────────────────────────────────────────────────────┐
│                         Slack                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ #note-business チャンネル                                │   │
│  │                                                         │   │
│  │ 🐦 本日のツイート提案                                    │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ 【案1】📢 記事宣伝                                   │ │   │
│  │ │ ADHDの「あとでやる」は永遠に来ない...😇              │ │   │
│  │ │                                                     │ │   │
│  │ │ ✅ ❌ ✏️  ← リアクションで操作                        │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼ 人間がリアクション追加              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Slack Workflow Builder                                   │   │
│  │ 「リアクションが追加されたとき」→ GitHub API を呼び出し   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼ repository_dispatch イベント（即時）
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions: check-reactions.yml                            │
│  → リアクション確認 → 承認されていれば /x-post で投稿           │
└─────────────────────────────────────────────────────────────────┘
```

---

## リアクション即時検知の仕組み

従来の「毎時ポーリング」ではなく、**Slack Workflow Builder** を使って即時トリガーを実現。

```
人間が ✅ リアクションを追加
         │
         ▼ （即時）
Slack Workflow Builder が検知
         │
         ▼
GitHub API (repository_dispatch) を呼び出し
         │
         ▼ （即時）
GitHub Actions: check-reactions.yml が起動
         │
         ▼
承認されたツイートを X に投稿
```

**メリット:**
- リアクション後、数秒〜数十秒で投稿実行
- ポーリング不要でコスト削減
- サーバー不要

---

## エージェント構成

### 使用するエージェント

| エージェント | ファイル | 役割 |
|-------------|---------|------|
| X運用エージェント | `.claude/agents/x-manager.md` | ツイート作成・投稿管理 |
| 戦略プランナー | `.claude/agents/strategy-planner.md` | テーマ提案・競合分析 |
| 記事ライター | `.claude/agents/note-writer.md` | 記事作成 |
| ビジネス統括 | `.claude/agents/note-business.md` | 全体管理 |

### 使用するスキル

| スキル | 用途 |
|--------|------|
| `/slack-ask` | 人間への質問をSlackに投稿 |
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
│       ├── slack-ask/            # Slack質問スキル
│       ├── x-post/               # X投稿スキル
│       ├── x-promotion/          # 記事宣伝スキル
│       └── ...
├── .github/workflows/
│   ├── daily-xpost.yml           # 毎日12:00: ツイート提案
│   ├── daily-trend.yml           # 毎日8:00: テーマ提案
│   ├── weekly-reflection.yml     # 毎週月曜: 振り返り
│   └── check-reactions.yml       # リアクション検知→実行（即時トリガー）
├── rules/
│   ├── x-posting-rules.md        # X投稿ルール
│   ├── strategy-rules.md         # 戦略ルール
│   └── ai-learnings.md           # AI学習ログ
└── output/
    ├── pending/                  # 承認待ちデータ
    └── x_posts/                  # 投稿履歴
```

---

## GitHub Actions ワークフロー

| ワークフロー | トリガー | 処理内容 |
|------------|---------|---------|
| `daily-xpost.yml` | 毎日 12:00 JST | Claude Code CLI でX運用エージェント実行 |
| `daily-trend.yml` | 毎日 8:00 JST | Claude Code CLI で戦略プランナー実行 |
| `weekly-reflection.yml` | 毎週月曜 9:00 JST | Claude Code CLI で振り返りエージェント実行 |
| `check-reactions.yml` | **Slack リアクション（即時）** | リアクション確認→承認されたら投稿 |

---

## 必要な設定

### 1. GitHub Secrets

リポジトリの Settings → Secrets and variables → Actions で設定:

```
ANTHROPIC_API_KEY    # Claude API キー
SLACK_BOT_TOKEN      # Slack Bot Token (xoxb-xxx)
SLACK_CHANNEL        # 投稿先チャンネルID (C0B0P1C07UY)
X_API_KEY            # X API キー
X_API_KEY_SECRET     # X API シークレット
X_ACCESS_TOKEN       # X アクセストークン
X_ACCESS_TOKEN_SECRET # X アクセストークンシークレット
```

### 2. GitHub Personal Access Token (PAT)

Slack から GitHub Actions をトリガーするために必要。

1. https://github.com/settings/tokens?type=beta にアクセス
2. 「Generate new token」をクリック
3. 設定:
   - Token name: `slack-workflow-trigger`
   - Expiration: 90 days（または No expiration）
   - Repository access: `Only select repositories` → `kocchan/note-uploader`
   - Permissions:
     - Repository permissions → **Contents**: Read and write
     - Repository permissions → **Metadata**: Read-only
4. 「Generate token」をクリック
5. トークンをコピー（`github_pat_xxx...`）

**重要**: このトークンは後で Slack Workflow Builder で使用します。

### 3. Slack App 設定（完了済み）

1. https://api.slack.com/apps でアプリ作成
2. Bot Token Scopes:
   - `chat:write`
   - `reactions:read`
   - `reactions:write`
   - `channels:history`
   - `channels:read`
3. アプリをワークスペースにインストール
4. Bot Token をコピーして GitHub Secrets に設定

### 4. Slack Workflow Builder 設定

Slack でリアクションが追加されたときに GitHub Actions をトリガーする設定。

#### 4.1 ワークフロー作成

1. Slack を開く
2. 左サイドバーの「**自動化**」または「**その他**」→「**自動化**」をクリック
3. 「**新しいワークフロー**」→「**ワークフローを作成する**」

#### 4.2 トリガー設定

1. 「**チャンネルでリアクションが追加されたとき**」を選択
2. 設定:
   - チャンネル: `#note-business`
   - リアクション: ✅ (`white_check_mark`)

#### 4.3 ステップ追加: Webhook を送信

1. 「**ステップを追加**」→「**Webhook を送信**」
2. 設定:

**URL:**
```
https://api.github.com/repos/kocchan/note-uploader/dispatches
```

**Method:** POST

**Headers:**
```
Authorization: Bearer github_pat_xxxxxxxxxx（あなたのPAT）
Accept: application/vnd.github.v3+json
Content-Type: application/json
```

**Body:**
```json
{
  "event_type": "slack-reaction"
}
```

#### 4.4 ワークフローを公開

1. 「**公開する**」をクリック
2. ワークフロー名: `GitHub Actions トリガー`

---

## 自動化フロー

### フロー1: X投稿自動化（即時トリガー版）

```
[GitHub Actions: 毎日 12:00]
         │
         ▼
[Claude Code CLI 起動]
  エージェントがツイート案を2-3個作成
         │
         ▼
[/slack-ask スキル実行]
         │ Slack に投稿案を送信
         │ リアクション追加: ✅ ❌ ✏️
         │ 状態を output/pending/ に保存
         ▼
┌─────────────────────────────────────┐
│ Slack: #note-business               │
│ 🐦 本日のツイート提案                │
│ ✅ ❌ ✏️                             │
└─────────────────────────────────────┘
         │
         │ 人間が ✅ をクリック
         ▼ （即時）
[Slack Workflow Builder が検知]
         │
         ▼
[GitHub API: repository_dispatch]
         │
         ▼ （即時）
[GitHub Actions: check-reactions.yml]
         │
         ▼
[リアクション確認 → /x-post 実行]
         │
         ▼
[Slack: 「✅ 投稿完了」と返信]
[X に投稿される]
```

### フロー2: テーマ提案

```
[GitHub Actions: 毎日 8:00]
         │
         ▼
[Claude Code CLI 起動]
  戦略プランナーがテーマ3案を作成
         │
         ▼
[/slack-ask スキル実行]
         │ リアクション: 1️⃣ 2️⃣ 3️⃣ 🔄 ⏸️
         ▼
    （人間がリアクションするまで待機）
         │
         ▼ （即時）
[Slack Workflow Builder → GitHub Actions]
         │
         ▼
[選択されたテーマを state.json に保存]
```

### フロー3: 週次振り返り

```
[GitHub Actions: 毎週月曜 9:00]
         │
         ▼
[Claude Code CLI 起動]
  振り返りレポート生成
         │
         ▼
[/slack-ask スキル実行]
         │ リアクション: 📝 ✅ 👍
         ▼
    （人間がリアクションするまで待機）
         │
         ▼ （即時）
[Slack Workflow Builder → GitHub Actions]
         │
         ├─ 📝 → rules/ai-learnings.md に追記
         └─ ✅ → 戦略ルールを更新
```

---

## 新規スキル: /slack-ask

人間への質問をSlackに投稿し、非同期で回答を待つスキル。

### 機能

1. **メッセージ投稿**: Slack チャンネルに質問・提案を投稿
2. **リアクション追加**: 選択肢に応じたリアクションを追加
3. **状態保存**: 回答待ち状態を `output/pending/` に保存
4. **メタデータ記録**: message_ts, channel_id を記録

### 使用例

```
/slack-ask "以下のツイート案から選んでください" --options "✅,❌,✏️" --tweets tweets.json
```

---

## 技術スタック

| コンポーネント | 技術 | 備考 |
|--------------|------|------|
| スケジューラー | GitHub Actions | cron式で定期実行 |
| 即時トリガー | Slack Workflow Builder | リアクション検知→GitHub API |
| エージェント実行 | Claude Code CLI | 内部で Claude API を呼ぶ（ANTHROPIC_API_KEY 必要） |
| エージェント定義 | `.claude/agents/*.md` | 既存のエージェントをそのまま使用 |
| スキル | `.claude/skills/*/SKILL.md` | 既存のスキルをそのまま使用 |
| Slack連携 | slack-sdk (Python) | Bot Token使用 |
| X投稿 | tweepy (X API v2) | 既存の /x-post スキル |
| 状態管理 | リポジトリ内JSON | output/に保存 |

**注意**: Claude Code CLI は Claude API のラッパーです。直接 API を呼ぶコードを書く必要はありませんが、`ANTHROPIC_API_KEY` は GitHub Secrets に設定が必要です。

---

## 実装ステップ

### Step 1: スキル作成 ✅
- [x] `/slack-ask` スキル作成
- [x] Slack投稿・リアクション追加機能
- [x] 状態保存機能

### Step 2: GitHub Actions 更新 ✅
- [x] daily-xpost.yml を Claude Code CLI 方式に変更
- [x] daily-trend.yml を Claude Code CLI 方式に変更
- [x] weekly-reflection.yml を Claude Code CLI 方式に変更
- [x] check-reactions.yml を即時トリガー対応に変更

### Step 3: 即時トリガー設定 ⏳
- [ ] GitHub Personal Access Token 作成
- [ ] Slack Workflow Builder 設定
- [ ] トリガーテスト

### Step 4: デプロイ ⏳
- [x] Slack App 作成
- [x] GitHub Secrets 設定
- [ ] 手動実行でテスト
- [ ] 本番運用開始

---

## 従来方式との比較

| 項目 | 従来（ポーリング） | 新方式（即時トリガー） |
|------|------------------|----------------------|
| リアクション検知 | 最大1時間待ち | **即時**（数秒） |
| コスト | ポーリングで分数消費 | **トリガー時のみ** |
| 仕組み | GitHub Actions cron | Slack Workflow Builder |

---

## 費用

| サービス | 費用 |
|---------|------|
| GitHub Actions | **無料**（即時トリガーで分数節約） |
| Claude API | ~$5-15/月（エージェント利用で増加） |
| X API | ~$0.10/月（10投稿 × $0.01） |
| **合計** | **~$5-16/月** |

---

## メリット

1. **即時実行**: リアクション後すぐに投稿される
2. **エージェント活用**: ローカルで作成したエージェントをそのまま自動実行
3. **スキル再利用**: `/x-post`, `/x-promotion` などをそのまま使用
4. **自律的な判断**: エージェントがルールを参照して自律的に判断
5. **コスト効率**: ポーリング不要で GitHub Actions の分数を節約
6. **AWS不要**: GitHub Actionsだけで完結

## 制限事項

1. **PAT 有効期限**: GitHub Personal Access Token は定期的に更新が必要
2. **実行時間制限**: GitHub Actions は最大6時間
3. **コスト増**: エージェント利用でAPI使用量が増加

---

## 次のアクション

1. **GitHub Personal Access Token 作成**
2. **Slack Workflow Builder 設定**
3. **手動実行テスト**: Actions → daily-xpost → Run workflow
4. **本番運用開始**
