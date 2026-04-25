# Cloudflare Workers - Slack Webhook

Slack Events を受信して GitHub Actions をトリガーする Worker。

## デプロイ手順

### 1. Cloudflare アカウント作成

https://dash.cloudflare.com/sign-up でアカウントを作成（無料）

### 2. Wrangler CLI インストール

```bash
npm install -g wrangler
wrangler login
```

### 3. Secrets 設定

```bash
cd cloudflare
wrangler secret put GITHUB_PAT
# → GitHub Personal Access Token を入力

wrangler secret put SLACK_SIGNING_SECRET
# → Slack App の Signing Secret を入力
```

### 4. デプロイ

```bash
wrangler deploy
```

デプロイ後、URL が表示されます（例: `https://note-business-slack-worker.your-subdomain.workers.dev`）

### 5. Slack App 設定

1. https://api.slack.com/apps → アプリを選択
2. **Event Subscriptions** → Enable Events: **On**
3. **Request URL** に以下を設定:
   ```
   https://note-business-slack-worker.your-subdomain.workers.dev/slack/events
   ```
4. URL が検証されたら、**Subscribe to bot events** で以下を追加:
   - `app_mention`
   - `reaction_added`

5. **Save Changes** をクリック

## 環境変数

| 変数名 | 説明 | 設定場所 |
|--------|------|----------|
| `GITHUB_PAT` | GitHub Personal Access Token (repo scope) | Secret |
| `SLACK_SIGNING_SECRET` | Slack App の Signing Secret | Secret |
| `GITHUB_REPO` | リポジトリ名 (owner/repo) | wrangler.toml |

## トリガーするイベント

| Slack Event | GitHub Event Type | 説明 |
|-------------|-------------------|------|
| `app_mention` | `slack-command` | @note-bot へのメンション |
| `reaction_added` | `slack-reaction` | リアクション追加 |

## ローカルテスト

```bash
wrangler dev
```

## ログ確認

```bash
wrangler tail
```
