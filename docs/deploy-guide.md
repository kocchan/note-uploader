# デプロイガイド（GitHub Actions + Claude Code CLI版）

GitHub Actions + Claude Code CLI + Slack でnote-businessを自動化する手順書。

## 前提条件

- GitHub リポジトリ（**パブリック推奨**：Actions無制限）
- Slack ワークスペース
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

### 2.2 チャンネルIDを取得

1. チャンネル名をクリック
2. モーダル下部に表示されるID（例: `C0B0P1C07UY`）をコピー

### 2.3 Bot をチャンネルに招待

チャンネルで:
```
/invite @note-business-bot
```

---

## Step 3: リポジトリをパブリックに変更

GitHub Actions を無制限で使うために推奨。

1. https://github.com/kocchan/note-uploader/settings にアクセス
2. 一番下の「Danger Zone」セクションへスクロール
3. 「Change repository visibility」→「Change to public」

**注意**: APIキーは GitHub Secrets に保存されているため、公開しても安全です。

---

## Step 4: GitHub Secrets 設定

リポジトリの **Settings** → **Secrets and variables** → **Actions** で以下を設定:

| Secret名 | 値 | 取得元 |
|---------|-----|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-xxx...` | https://console.anthropic.com |
| `SLACK_BOT_TOKEN` | `xoxb-xxx...` | Slack App → OAuth & Permissions |
| `SLACK_CHANNEL` | `C0B0P1C07UY` | チャンネルID（#ではなくIDを使用） |
| `X_API_KEY` | `xxx` | X Developer Portal |
| `X_API_KEY_SECRET` | `xxx` | X Developer Portal |
| `X_ACCESS_TOKEN` | `xxx` | X Developer Portal |
| `X_ACCESS_TOKEN_SECRET` | `xxx` | X Developer Portal |

---

## Step 5: 動作確認

### 5.1 手動実行テスト

1. リポジトリの **Actions** タブを開く
2. 左側から **Daily X Post Suggestions** を選択
3. **Run workflow** → **Run workflow** をクリック
4. 実行が完了するまで待つ（約2-5分）

### 5.2 Slack 確認

`#note-business` チャンネルにツイート提案が投稿されていることを確認

### 5.3 リアクションテスト

1. ツイート案に ✅ リアクションを追加
2. **Check Slack Reactions & Execute** を手動実行（または5分待つ）
3. X に投稿されたことを確認

---

## Step 6: 本番運用開始

すべての動作確認が完了したら、自動実行が開始されます:

| ワークフロー | スケジュール |
|------------|-------------|
| テーマ提案 | 毎日 8:00 JST |
| ツイート提案 | 毎日 12:00 JST |
| リアクションチェック | **5分ごと** |
| 週次振り返り | 毎週月曜 9:00 JST |

---

## トラブルシューティング

### Slack にメッセージが投稿されない

1. **Bot Token 確認**: Secrets の `SLACK_BOT_TOKEN` が正しいか
2. **チャンネルID確認**: `SLACK_CHANNEL` がチャンネルID（Cで始まる）か
3. **チャンネル招待**: Bot がチャンネルに招待されているか
4. **権限確認**: `chat:write` スコープがあるか

### リアクションが検知されない

1. **リアクション権限**: `reactions:read` スコープがあるか
2. **チャンネル履歴**: `channels:history` スコープがあるか
3. **Bot のリアクション**: Bot 自身のリアクションは無視される（count > 1 で検知）
4. **pending ファイル**: `output/pending/` にJSONファイルがあるか確認

### X 投稿が失敗する

1. **API クレデンシャル**: Secrets が正しいか
2. **API 残高**: X Developer Portal でクレジット残高を確認
3. **文字数**: 280文字を超えていないか

### GitHub Actions が実行されない

1. **スケジュール**: cron は UTC 時間（JST - 9時間）
2. **パブリック確認**: プライベートリポジトリの場合、分数制限に注意
3. **ワークフロー有効化**: Actions が無効になっていないか確認
4. **ログ確認**: Actions → 該当ワークフロー → 失敗したジョブのログを確認

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

### 保留中のデータ

```
output/pending/YYYYMMDD_tweets.json
```

---

## 費用

| サービス | 月額 |
|---------|------|
| GitHub Actions | **無料**（パブリックリポジトリ無制限） |
| Claude API | ~$5-15（Claude Code CLI 経由で使用量増加） |
| X API | ~$0.10（10投稿 × $0.01） |
| **合計** | **~$5-16/月** |

---

## 技術構成

```
GitHub Actions (スケジューラー)
       │
       ▼
Claude Code CLI
       │ claude -p "タスク" --dangerously-skip-permissions
       │
       ├─ .claude/agents/ (エージェント定義)
       ├─ .claude/skills/ (スキル)
       └─ rules/ (ルール)
       │
       ▼
Slack API (投稿・リアクション)
       │
       ▼
X API (ツイート投稿)
```

---

## 次のステップ

1. ✅ Slack App 作成
2. ✅ GitHub Secrets 設定
3. ✅ リポジトリをパブリックに変更
4. ✅ 手動実行テスト
5. □ 本番運用開始
6. □ 運用しながらルールを調整
