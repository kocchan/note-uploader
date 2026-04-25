# デプロイガイド（GitHub Actions版）

GitHub Actions + Slack でnote-businessを自動化する手順書。

## 前提条件

- GitHub リポジトリ
- Slack ワークスペースの管理者権限
- Claude API キー
- X API クレデンシャル（設定済み）

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
reactions:read      # リアクション読み取り
reactions:write     # リアクション追加
channels:history    # チャンネル履歴読み取り
channels:read       # チャンネル一覧取得
```

### 1.3 アプリをインストール

**OAuth & Permissions** → **Install to Workspace**

### 1.4 トークン取得

**Bot User OAuth Token** をコピー: `xoxb-xxx...`

---

## Step 2: Slack チャンネル設定

### 2.1 チャンネル作成

Slackで `#note-business` チャンネルを作成（または既存チャンネルを使用）

### 2.2 Bot をチャンネルに招待

チャンネルで:
```
/invite @note-business-bot
```

---

## Step 3: GitHub Secrets 設定

リポジトリの **Settings** → **Secrets and variables** → **Actions** で以下を設定:

| Secret名 | 値 | 取得元 |
|---------|-----|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-xxx...` | https://console.anthropic.com |
| `SLACK_BOT_TOKEN` | `xoxb-xxx...` | Slack App → OAuth & Permissions |
| `SLACK_CHANNEL` | `#note-business` | 投稿先チャンネル名 |
| `X_API_KEY` | `xxx` | X Developer Portal |
| `X_API_KEY_SECRET` | `xxx` | X Developer Portal |
| `X_ACCESS_TOKEN` | `xxx` | X Developer Portal |
| `X_ACCESS_TOKEN_SECRET` | `xxx` | X Developer Portal |

---

## Step 4: 動作確認

### 4.1 手動実行テスト

1. リポジトリの **Actions** タブを開く
2. 左側から **Daily X Post Suggestions** を選択
3. **Run workflow** → **Run workflow** をクリック
4. 実行が完了するまで待つ（約1-2分）

### 4.2 Slack 確認

`#note-business` チャンネルにツイート提案が投稿されていることを確認

### 4.3 リアクションテスト

1. ツイート案に ✅ リアクションを追加
2. **Check Slack Reactions & Execute** を手動実行
3. X に投稿されたことを確認

---

## Step 5: 本番運用開始

すべての動作確認が完了したら、自動実行が開始されます:

| ワークフロー | スケジュール |
|------------|-------------|
| トレンド収集 | 毎日 8:00 JST |
| ツイート提案 | 毎日 12:00 JST |
| リアクションチェック | 毎時 |
| 週次振り返り | 毎週月曜 9:00 JST |

---

## トラブルシューティング

### Slack にメッセージが投稿されない

1. **Bot Token 確認**: Secrets の `SLACK_BOT_TOKEN` が正しいか
2. **チャンネル招待**: Bot がチャンネルに招待されているか
3. **権限確認**: `chat:write` スコープがあるか

### リアクションが検知されない

1. **リアクション権限**: `reactions:read` スコープがあるか
2. **チャンネル履歴**: `channels:history` スコープがあるか
3. **Bot のリアクション**: Bot 自身のリアクションは無視される（人間のリアクションのみ検知）

### X 投稿が失敗する

1. **API クレデンシャル**: Secrets が正しいか
2. **API 残高**: X Developer Portal でクレジット残高を確認
3. **文字数**: 280文字（Twitter換算）を超えていないか

### GitHub Actions が実行されない

1. **スケジュール**: cron は UTC 時間（JST - 9時間）
2. **ワークフロー有効化**: Actions が無効になっていないか確認
3. **ログ確認**: Actions → 該当ワークフロー → 失敗したジョブのログを確認

---

## ログの確認方法

### GitHub Actions ログ

1. リポジトリ → **Actions** タブ
2. 実行履歴から確認したいワークフローを選択
3. ジョブ → ステップを展開してログを確認

### 投稿履歴

```
output/x_posts/post_history.md
```

### 保留中のツイート

```
output/pending_tweets/YYYYMMDD_slack.json
```

---

## 費用

| サービス | 月額 |
|---------|------|
| GitHub Actions | **無料**（パブリックリポジトリ無制限、プライベート2,000分/月） |
| Claude API | ~$1-5（使用量による） |
| X API | ~$0.10（10投稿 × $0.01） |
| **合計** | **~$1-6/月** |

---

## 次のステップ

1. ✅ Slack App 作成
2. ✅ GitHub Secrets 設定
3. ✅ 手動実行テスト
4. □ 本番運用開始
5. □ 運用しながらルールを調整
