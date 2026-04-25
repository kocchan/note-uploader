# デプロイガイド（Slack MCP + Cloudflare Workers版）

GitHub Actions + Claude Code CLI + Slack MCP + Cloudflare Workers でnote-businessを自動化する手順書。

## 前提条件

- GitHub リポジトリ（**パブリック推奨**：Actions無制限）
- Slack ワークスペース
- Cloudflare アカウント（無料）
- Claude API キー
- X API クレデンシャル（設定済み）

---

## Step 1: Slack App 設定

### 1.1 アプリ作成（完了済みの場合はスキップ）

1. https://api.slack.com/apps にアクセス
2. 「Create New App」をクリック
3. 「From scratch」を選択
4. App Name: `note-business-bot`
5. Workspace: あなたのワークスペースを選択

### 1.2 Bot Token Scopes 設定

**OAuth & Permissions** → **Scopes** → **Bot Token Scopes** で以下を追加:

```
app_mentions:read   # メンション読み取り
channels:history    # チャンネル履歴読み取り
channels:read       # チャンネル一覧取得
chat:write          # メッセージ送信
reactions:read      # リアクション読み取り
reactions:write     # リアクション追加
users:read          # ユーザー情報取得
```

### 1.3 アプリを再インストール（Scopes変更後）

**OAuth & Permissions** → **Reinstall to Workspace**

### 1.4 Signing Secret 取得

**Basic Information** → **App Credentials** → **Signing Secret** をコピー

### 1.5 Team ID 取得

Slack ワークスペースの Team ID を取得:
1. Slackをブラウザで開く
2. URLの `https://app.slack.com/client/T0XXXXXXX/...` の `T0XXXXXXX` 部分がTeam ID

---

## Step 2: Cloudflare Workers デプロイ

### 2.1 Cloudflare アカウント作成

https://dash.cloudflare.com/sign-up でアカウント作成（無料）

### 2.2 Wrangler CLI インストール

```bash
npm install -g wrangler
wrangler login
```

### 2.3 Workers デプロイ

```bash
cd cloudflare
wrangler secret put GITHUB_PAT
# → GitHub Personal Access Token を入力（repo scope必要）

wrangler secret put SLACK_SIGNING_SECRET
# → Slack App の Signing Secret を入力

wrangler deploy
```

デプロイ後、URL が表示されます:
```
https://note-business-slack-worker.YOUR-SUBDOMAIN.workers.dev
```

### 2.4 Slack Event Subscriptions 設定

1. https://api.slack.com/apps → アプリを選択
2. **Event Subscriptions** → Enable Events: **On**
3. **Request URL** に以下を設定:
   ```
   https://note-business-slack-worker.YOUR-SUBDOMAIN.workers.dev/slack/events
   ```
4. URL が検証されたら、**Subscribe to bot events** で以下を追加:
   - `app_mention` - @note-bot へのメンション
   - `reaction_added` - リアクション追加
5. **Save Changes** をクリック

---

## Step 3: GitHub Secrets 設定

リポジトリの **Settings** → **Secrets and variables** → **Actions** で以下を設定:

| Secret名 | 値 | 取得元 |
|---------|-----|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-xxx...` | https://console.anthropic.com |
| `SLACK_BOT_TOKEN` | `xoxb-xxx...` | Slack App → OAuth & Permissions |
| `SLACK_TEAM_ID` | `T0xxx...` | Slack URL から取得 |
| `SLACK_CHANNEL` | `C0B0P1C07UY` | チャンネルID（#ではなくIDを使用） |
| `GITHUB_PAT` | `ghp_xxx...` | GitHub Settings → Developer settings → PAT |
| `X_API_KEY` | `xxx` | X Developer Portal |
| `X_API_KEY_SECRET` | `xxx` | X Developer Portal |
| `X_ACCESS_TOKEN` | `xxx` | X Developer Portal |
| `X_ACCESS_TOKEN_SECRET` | `xxx` | X Developer Portal |

---

## Step 4: 動作確認

### 4.1 定期実行テスト

1. リポジトリの **Actions** タブを開く
2. 左側から **Daily X Post Suggestions** を選択
3. **Run workflow** → **Run workflow** をクリック
4. 実行が完了するまで待つ（約2-5分）
5. Slack `#note-business` にツイート提案が投稿されていることを確認

### 4.2 即時トリガーテスト（リアクション）

1. Slack のツイート案に ✅ リアクションを追加
2. **約1-3秒後**に GitHub Actions が起動することを確認
3. X に投稿されたことを確認
4. Slack スレッドに「✅ 投稿完了」と返信されていることを確認

### 4.3 即時トリガーテスト（メンション）

1. Slack で `@note-bot ツイート案を作って` と送信
2. **約1-3秒後**に GitHub Actions が起動することを確認
3. スレッドに返信が来ることを確認

---

## Step 5: 本番運用開始

すべての動作確認が完了したら、自動実行が開始されます:

| ワークフロー | トリガー | 説明 |
|------------|---------|------|
| テーマ提案 | 毎日 8:00 JST | 記事テーマを提案 |
| ツイート提案 | 毎日 12:00 JST | ツイート案を提案 |
| 週次振り返り | 毎週月曜 9:00 JST | 週次レポート |
| Slack コマンド | **即時** | @note-bot へのメンション |
| Slack リアクション | **即時** | ✅❌✏️ などのリアクション |

---

## トラブルシューティング

### Slack にメッセージが投稿されない

1. **SLACK_BOT_TOKEN 確認**: GitHub Secrets が正しいか
2. **SLACK_TEAM_ID 確認**: Team ID が正しいか
3. **チャンネル招待**: Bot がチャンネルに招待されているか
4. **MCP 設定**: mcp.json が正しく設定されているか

### 即時トリガーが動かない

1. **Cloudflare Workers ログ確認**:
   ```bash
   cd cloudflare
   wrangler tail
   ```
2. **Slack Event Subscriptions**: Request URL が検証されているか
3. **GITHUB_PAT**: repo scope があるか
4. **SLACK_SIGNING_SECRET**: 正しい値か

### X 投稿が失敗する

1. **API クレデンシャル**: Secrets が正しいか
2. **API 残高**: X Developer Portal でクレジット残高を確認
3. **文字数**: 280文字を超えていないか

### GitHub Actions が実行されない

1. **スケジュール**: cron は UTC 時間（JST - 9時間）
2. **パブリック確認**: プライベートリポジトリの場合、分数制限に注意
3. **ログ確認**: Actions → 該当ワークフロー → 失敗したジョブのログを確認

---

## ログの確認方法

### GitHub Actions ログ

1. リポジトリ → **Actions** タブ
2. 実行履歴から確認したいワークフローを選択
3. ジョブ → ステップを展開してログを確認

### Cloudflare Workers ログ

```bash
cd cloudflare
wrangler tail
```

### 投稿履歴

```
output/x_posts/post_history.md
```

---

## 費用

| サービス | 月額 |
|---------|------|
| GitHub Actions | **無料**（パブリックリポジトリ無制限） |
| Cloudflare Workers | **無料**（10万リクエスト/日まで） |
| Claude API | ~$5-15 |
| X API | ~$0.10（10投稿 × $0.01） |
| **合計** | **~$5-16/月** |

---

## アーキテクチャ概要

```
Slack
  │
  ├─ @note-bot メンション ─────┐
  │                           │
  └─ ✅ リアクション ──────────┤
                              │ Slack Events API
                              ▼
                    Cloudflare Workers
                              │ repository_dispatch
                              ▼
                    GitHub Actions
                              │
                              ├─ Claude Code CLI
                              │     └─ Slack MCP
                              │
                              └─ X API (tweepy)
```

---

## 次のステップ

1. ✅ Slack App 設定（Scopes追加）
2. ✅ Cloudflare Workers デプロイ
3. ✅ Slack Event Subscriptions 設定
4. ✅ GitHub Secrets 設定（SLACK_TEAM_ID, GITHUB_PAT追加）
5. □ 手動実行テスト
6. □ 即時トリガーテスト
7. □ 本番運用開始
