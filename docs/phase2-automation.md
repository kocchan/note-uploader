# Phase 2: 自動化アーキテクチャ設計

## 概要

AWS Lambda + Slack Bolt を使って、エージェントが自律的に動作し、人間レビューをSlack上で完結させる。

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                 AWS Lambda (EventBridge Scheduler)              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ 毎日 8:00    │ │ 毎日 12:00   │ │ 毎週月曜 9:00            │ │
│  │ トレンド収集 │ │ X投稿提案    │ │ 振り返り                 │ │
│  └──────┬───────┘ └──────┬───────┘ └────────────┬─────────────┘ │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude API (claude-3-5-sonnet)               │
│                                                                 │
│  ルール読み込み → 成果物生成 → Slackに送信                       │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│              Slack Bolt App (Lambda + API Gateway)              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ #note-business チャンネル                                │   │
│  │                                                         │   │
│  │ 🤖 Bot: ツイート投稿の提案                               │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ ADHDの「あとでやる」は永遠に来ない...😇              │ │   │
│  │ │ だからChatGPTに外注することにした!                   │ │   │
│  │ │                                                     │ │   │
│  │ │ [✅ このまま投稿] [✏️ 修正する] [❌ キャンセル]       │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ボタン押下 → Lambda実行 → X API投稿 → 結果をSlackに通知       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 実装済みコンポーネント

### ディレクトリ構成

```
312_note/
├── src/
│   ├── slack/
│   │   ├── app.py                 # Slack Bolt メインアプリ (Lambda対応)
│   │   └── handlers/
│   │       └── x_post_handler.py  # X投稿処理・レビューUI
│   ├── scheduled/
│   │   ├── daily_trend.py         # 毎日8:00: トレンド収集→テーマ提案
│   │   ├── daily_xpost.py         # 毎日12:00: X投稿案の生成
│   │   └── weekly_reflection.py   # 毎週月曜9:00: 振り返りレポート
│   └── requirements.txt           # Python依存パッケージ
├── template.yaml                  # AWS SAM テンプレート
└── docs/
    ├── phase2-automation.md       # 本ドキュメント
    └── deploy-guide.md            # デプロイ手順書
```

### Lambda関数一覧

| 関数名 | トリガー | 処理内容 |
|--------|---------|---------|
| `note-business-slack-bot` | API Gateway | Slackイベント処理（ボタン押下等） |
| `note-business-daily-trend` | EventBridge (毎日8:00 JST) | トレンド収集→テーマ提案 |
| `note-business-daily-xpost` | EventBridge (毎日12:00 JST) | X投稿案の生成→Slack送信 |
| `note-business-weekly-reflection` | EventBridge (毎週月曜9:00 JST) | 振り返り→戦略更新提案 |

---

## 自動化フロー

### フロー1: X投稿自動化（実装済み）

```
[Lambda: 毎日 12:00 JST]
     │
     ▼
[Claude API: ツイート案を2-3個生成]
     │ ルール参照: rules/x-posting-rules.md
     │ 状態参照: output/state.json
     ▼
[Slack: レビュー依頼送信]
     │
     ├─ [✅ このまま投稿]
     │        │
     │        ▼
     │   [X API: 自動投稿]
     │        │
     │        ▼
     │   [Slack: 投稿完了通知 + URL]
     │   [履歴更新: output/x_posts/post_history.md]
     │
     ├─ [✏️ 修正する]
     │        │
     │        ▼
     │   [Slack: 修正モーダル表示]
     │        │
     │        ▼
     │   [修正後、X APIで投稿]
     │
     └─ [❌ キャンセル]
              │
              ▼
         [Slack: キャンセル通知]
```

### フロー2: トレンド収集→テーマ提案

```
[Lambda: 毎日 8:00 JST]
     │
     ▼
[Claude API: トレンド分析]
     │ ルール参照: rules/strategy-rules.md
     │ 学び参照: rules/ai-learnings.md
     ▼
[テーマ3案を生成]
     │
     ▼
[Slack: テーマ選択メッセージ送信]
     │
     ├─ [1️⃣ を選択]
     │        │
     │        ▼
     │   [state.json更新]
     │        │
     │        ▼
     │   [次: 構成作成フロー開始]
     │
     ├─ [🔄 別の提案]
     │        │
     │        ▼
     │   [再度テーマ生成]
     │
     └─ [⏸️ 今日はスキップ]
              │
              ▼
         [何もしない]
```

### フロー3: 週次振り返り

```
[Lambda: 毎週月曜 9:00 JST]
     │
     ▼
[Claude API: 先週の活動を分析]
     │ 参照: output/x_posts/post_history.md
     │ 参照: output/state.json
     │ 参照: rules/ai-learnings.md
     ▼
[振り返りレポート生成]
     │ - 達成したこと
     │ - 課題
     │ - 学び
     │ - 戦略更新提案
     ▼
[Slack: レポート送信]
     │
     ├─ [📝 学びをルールに追記]
     │        │
     │        ▼
     │   [rules/ai-learnings.md に追記]
     │
     └─ [✅ 戦略更新を採用]
              │
              ▼
         [rules/strategy-rules.md を更新]
```

---

## Slackメッセージ例

### X投稿レビュー

```
🐦 ツイート投稿の提案

━━━━━━━━━━━━━━━━━━━━━━━━

ADHDの「あとでやる」は永遠に来ない...😇

だからChatGPTに外注することにした!

具体的なプロンプト5つをnoteにまとめました👍
https://note.com/xxx

━━━━━━━━━━━━━━━━━━━━━━━━

📝 文字数: 89/280 ✅
💡 理由: 記事宣伝 + 共感を誘う導入

[✅ このまま投稿] [✏️ 修正する] [❌ キャンセル]
```

### テーマ提案

```
🎯 新しい記事テーマを提案します

━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Claude × ADHD仕事術
   👥 ターゲット: Claude未経験のADHD当事者
   💎 価値: 初期設定から使い方まで完全ガイド
   🔥 需要: 高 | 🌟 競合: 少

2️⃣ AI習慣化コーチ
   👥 ターゲット: 三日坊主に悩むADHD
   💎 価値: AIで習慣を維持する仕組み
   📈 需要: 中 | 🎯 競合: 中

3️⃣ タスク管理プロンプト集
   👥 ターゲット: タスク管理ツールが続かない人
   💎 価値: すぐ使えるプロンプト10選
   🔥 需要: 高 | ⚔️ 競合: 多

━━━━━━━━━━━━━━━━━━━━━━━━

[1️⃣ を選択] [2️⃣ を選択] [3️⃣ を選択] [🔄 別の提案] [⏸️ スキップ]
```

### 週次振り返り

```
📊 週次振り返りレポート

━━━━━━━━━━━━━━━━━━━━━━━━

**サマリー**
先週はX投稿を5件実施。エンゲージメント率は平均3.2%で前週比+0.5%。

**✅ 達成したこと**
• X投稿の定期化（毎日1件）
• 共感ツイートの反応が良好

**⚠️ 課題**
• 記事宣伝ツイートのクリック率が低い
• 投稿時間が不規則

**💡 学び**
• 「...!」で終わるツイートの反応が良い
• 午後8時台の投稿が最も反応がある

━━━━━━━━━━━━━━━━━━━━━━━━

**🎯 来週の注力ポイント**
投稿時間を20:00に固定し、記事宣伝の表現を改善

**🔧 戦略更新の提案**
1. X運用: 投稿時間を「ランダム」→「20:00固定」に変更
   [✅ 採用]

━━━━━━━━━━━━━━━━━━━━━━━━

[📝 学びをルールに追記] [👍 確認済み]
```

---

## 技術スタック

| コンポーネント | 技術 | 備考 |
|--------------|------|------|
| スケジューラー | AWS EventBridge | cron式で定期実行 |
| イベント処理 | AWS Lambda (Python 3.11) | サーバーレス |
| API エンドポイント | API Gateway | Slack Event受信 |
| Slack App | Slack Bolt for Python | Lambda対応 |
| AI実行 | Claude API | claude-3-5-sonnet-20241022 |
| X投稿 | tweepy (X API v2) | 既存のpost_tweet.py流用 |
| 状態管理 | リポジトリ内JSON | output/state.json |
| IaC | AWS SAM | template.yaml |

---

## 環境変数

```env
# Slack
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_SIGNING_SECRET=xxx
SLACK_CHANNEL=#note-business

# Claude
ANTHROPIC_API_KEY=sk-ant-xxx

# X (Twitter)
X_API_KEY=xxx
X_API_KEY_SECRET=xxx
X_ACCESS_TOKEN=xxx
X_ACCESS_TOKEN_SECRET=xxx
```

---

## Slack App 権限

### Bot Token Scopes

```
chat:write          # メッセージ送信
chat:write.public   # パブリックチャンネルに送信
commands            # スラッシュコマンド
files:write         # ファイルアップロード
```

### Interactivity

- Request URL: `https://xxx.execute-api.ap-northeast-1.amazonaws.com/Prod/slack/events`

---

## 実装ステップ

### Step 1: Slack App 基盤 ✅
- [x] Slack Bolt セットアップ (src/slack/app.py)
- [x] Lambda対応 (process_before_response=True)
- [x] ボタンハンドラー実装

### Step 2: X投稿レビューフロー ✅
- [x] 承認/却下/修正ボタン
- [x] 修正モーダル
- [x] X API投稿実行
- [x] 投稿履歴記録

### Step 3: 定期実行Lambda ✅
- [x] daily_xpost.py (毎日12:00)
- [x] daily_trend.py (毎日8:00)
- [x] weekly_reflection.py (毎週月曜9:00)

### Step 4: AWS SAM テンプレート ✅
- [x] template.yaml 作成
- [x] 環境変数設定
- [x] EventBridge スケジュール定義

### Step 5: デプロイ ⏳
- [ ] Slack App 作成 (api.slack.com)
- [ ] AWS SAM デプロイ (`sam deploy --guided`)
- [ ] Slack Interactivity URL 設定
- [ ] 動作確認

---

## 費用見積もり

| サービス | 月額見積もり |
|---------|-------------|
| Lambda | ~$0（無料枠: 100万リクエスト/月） |
| API Gateway | ~$1（100万リクエストまで$3.50） |
| CloudWatch Logs | ~$0.5 |
| X API | ~$0.10（10投稿 × $0.01） |
| Claude API | ~$1-5（使用量による） |
| **合計** | **~$3-7/月** |

---

## 次のアクション

1. **Slack App 作成**: https://api.slack.com/apps
2. **AWS SAM デプロイ**: `docs/deploy-guide.md` 参照
3. **動作確認**: `/note-status` コマンドでテスト
4. **本番運用開始**
