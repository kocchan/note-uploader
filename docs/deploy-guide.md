# デプロイガイド

AWS Lambda + Slack Bolt でnote-businessを自動化する手順書。

## 前提条件

- AWS アカウント
- AWS CLI インストール済み & 設定済み
- AWS SAM CLI インストール済み
- Slack ワークスペースの管理者権限

---

## Step 1: Slack App 作成

### 1.1 アプリ作成

1. https://api.slack.com/apps にアクセス
2. 「Create New App」をクリック
3. 「From scratch」を選択
4. App Name: `note-business-bot`
5. Workspace: あなたのワークスペースを選択

### 1.2 Bot Token Scopes 設定

**OAuth & Permissions** → **Scopes** → **Bot Token Scopes** で以下を追加:

```
chat:write          # メッセージ送信
chat:write.public   # パブリックチャンネルに送信
commands            # スラッシュコマンド
files:write         # ファイルアップロード
```

### 1.3 Interactivity 有効化

**Interactivity & Shortcuts** → **Interactivity** をON

Request URL は後で設定（Lambda デプロイ後）

### 1.4 Slash Commands 作成（オプション）

**Slash Commands** → **Create New Command**:

| Command | Request URL | Description |
|---------|-------------|-------------|
| `/note-status` | (後で設定) | 現在の状態を表示 |
| `/x-post-now` | (後で設定) | X投稿を手動実行 |

### 1.5 トークン取得

**OAuth & Permissions** → **Install to Workspace**

以下をメモ:
- **Bot User OAuth Token**: `xoxb-xxx...`
- **Signing Secret** (Basic Information内): `xxx...`

---

## Step 2: AWS 設定

### 2.1 AWS CLI 確認

```bash
aws --version
aws sts get-caller-identity  # 認証確認
```

### 2.2 SAM CLI インストール

```bash
# macOS
brew install aws-sam-cli

# 確認
sam --version
```

### 2.3 環境変数設定

```bash
# .env.deploy ファイルを作成（ローカル用）
cat > .env.deploy << 'EOF'
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
ANTHROPIC_API_KEY=sk-ant-your-key
X_API_KEY=your-x-api-key
X_API_KEY_SECRET=your-x-api-secret
X_ACCESS_TOKEN=your-x-access-token
X_ACCESS_TOKEN_SECRET=your-x-access-token-secret
SLACK_CHANNEL=#note-business
EOF
```

---

## Step 3: Lambda デプロイ

### 3.1 ビルド

```bash
cd /path/to/312_note
sam build
```

### 3.2 デプロイ（初回）

```bash
sam deploy --guided
```

プロンプトに従って入力:

```
Stack Name: note-business-stack
AWS Region: ap-northeast-1  # 東京リージョン
Confirm changes before deploy: y
Allow SAM CLI IAM role creation: y
Save arguments to samconfig.toml: y

# パラメータ入力
SlackBotToken: xoxb-xxx
SlackSigningSecret: xxx
AnthropicApiKey: sk-ant-xxx
XApiKey: xxx
XApiKeySecret: xxx
XAccessToken: xxx
XAccessTokenSecret: xxx
```

### 3.3 デプロイ（2回目以降）

```bash
sam deploy
```

### 3.4 API Gateway URL 確認

デプロイ完了後、出力される URL をメモ:

```
Outputs:
SlackBotApi: https://xxxxxxxxxx.execute-api.ap-northeast-1.amazonaws.com/Prod/slack/events
```

---

## Step 4: Slack App に URL 設定

### 4.1 Interactivity URL

**Interactivity & Shortcuts** → **Request URL**:
```
https://xxxxxxxxxx.execute-api.ap-northeast-1.amazonaws.com/Prod/slack/events
```

### 4.2 Slash Commands URL

各コマンドの **Request URL** を同じURLに設定

### 4.3 Event Subscriptions（オプション）

**Event Subscriptions** → ON → **Request URL** を設定

Subscribe to bot events:
- `app_mention`
- `message.channels`

---

## Step 5: 動作確認

### 5.1 Slack でテスト

```
/note-status
```

### 5.2 Lambda ログ確認

```bash
# CloudWatch Logs を確認
aws logs tail /aws/lambda/note-business-slack-bot --follow
```

### 5.3 手動で定期実行をテスト

```bash
# X投稿提案をテスト
aws lambda invoke \
  --function-name note-business-daily-xpost \
  --payload '{}' \
  response.json

cat response.json
```

---

## Step 6: チャンネル設定

### 6.1 専用チャンネル作成

Slackで `#note-business` チャンネルを作成

### 6.2 Bot をチャンネルに追加

チャンネルで `/invite @note-business-bot`

### 6.3 環境変数にチャンネル設定

Lambda のコンソールで環境変数 `SLACK_CHANNEL` を `#note-business` に設定

---

## 定期実行スケジュール

| Lambda | スケジュール | 内容 |
|--------|-------------|------|
| `daily-trend` | 毎日 8:00 JST | トレンド収集→テーマ提案 |
| `daily-xpost` | 毎日 12:00 JST | X投稿案の提案 |
| `weekly-reflection` | 毎週月曜 9:00 JST | 週次振り返り |

---

## トラブルシューティング

### Slack からのリクエストがタイムアウト

Slack は 3秒以内にレスポンスが必要。

→ `process_before_response=True` を設定済み。
→ 重い処理は別の Lambda で非同期実行

### Lambda がタイムアウト

`template.yaml` の `Timeout` を増やす（最大 900秒）

### 認証エラー

環境変数を確認:
```bash
aws lambda get-function-configuration \
  --function-name note-business-slack-bot \
  --query 'Environment.Variables'
```

---

## 費用見積もり

| サービス | 月額見積もり |
|---------|-------------|
| Lambda | ~$0（無料枠内） |
| API Gateway | ~$1 |
| CloudWatch Logs | ~$0.5 |
| **合計** | **~$1.5/月** |

※ リクエスト数が少なければほぼ無料

---

## 次のステップ

1. ✅ Slack App 作成
2. ✅ Lambda デプロイ
3. ✅ Interactivity 設定
4. □ 本番運用開始
5. □ 必要に応じてスケジュール調整
