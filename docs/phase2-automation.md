# Phase 2: 自動化アーキテクチャ設計

## 概要

GitHub Actions + Slack（リアクション方式）を使って、エージェントが自律的に動作し、人間レビューをSlack上で完結させる。

**AWS不要、GitHub Actionsのみで完結。**

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Scheduler)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ 毎日 8:00    │ │ 毎日 12:00   │ │ 毎週月曜 9:00            │ │
│  │ トレンド収集 │ │ X投稿提案    │ │ 振り返り                 │ │
│  └──────┬───────┘ └──────┬───────┘ └────────────┬─────────────┘ │
│         │                │                      │               │
│         │     ┌──────────┴──────────┐           │               │
│         │     │ 毎時チェック         │           │               │
│         │     │ リアクション確認     │           │               │
│         │     └──────────┬──────────┘           │               │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude API (claude-sonnet)                   │
│                                                                 │
│  ルール読み込み → 成果物生成 → Slackに投稿                       │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
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
│                                                                 │
│  ✅リアクション → GitHub Actions検知 → X API投稿               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 実装済みコンポーネント

### ディレクトリ構成

```
312_note/
├── .github/workflows/
│   ├── daily-xpost.yml        # 毎日12:00: ツイート提案
│   ├── daily-trend.yml        # 毎日8:00: テーマ提案
│   ├── weekly-reflection.yml  # 毎週月曜: 振り返り
│   └── check-reactions.yml    # 毎時: リアクションチェック→実行
├── scripts/
│   ├── generate_tweets.py     # Claude APIでツイート生成
│   ├── generate_themes.py     # Claude APIでテーマ生成
│   ├── generate_reflection.py # Claude APIで振り返り生成
│   ├── post_to_slack.py       # Slackにツイート案を投稿
│   ├── post_themes_to_slack.py
│   ├── post_reflection_to_slack.py
│   └── check_slack_reactions.py  # リアクション確認→X投稿
└── docs/
    └── phase2-automation.md   # 本ドキュメント
```

### GitHub Actions ワークフロー

| ワークフロー | スケジュール | 処理内容 |
|------------|-------------|---------|
| `daily-xpost.yml` | 毎日 12:00 JST | ツイート案生成→Slack投稿 |
| `daily-trend.yml` | 毎日 8:00 JST | テーマ提案→Slack投稿 |
| `weekly-reflection.yml` | 毎週月曜 9:00 JST | 振り返りレポート→Slack投稿 |
| `check-reactions.yml` | 毎時 | リアクション確認→承認されたら実行 |

---

## 自動化フロー

### フロー1: X投稿自動化

```
[GitHub Actions: 毎日 12:00]
         │
         ▼
[Claude API: ツイート案を2-3個生成]
         │ rules/x-posting-rules.md を参照
         ▼
[Slack: ツイート案を投稿]
         │ リアクション追加: ✅ ❌ ✏️
         ▼
    （人間がリアクションするまで待機）
         │
         ▼
[GitHub Actions: 毎時0分]
         │
         ▼
[Slackのリアクションをチェック]
         │
         ├─ ✅ がついている
         │        │
         │        ▼
         │   [X API: 自動投稿]
         │        │
         │        ▼
         │   [Slack: 「✅ 投稿完了」と返信]
         │   [履歴更新: output/x_posts/post_history.md]
         │
         ├─ ❌ がついている
         │        │
         │        ▼
         │   [Slack: 「スキップしました」と返信]
         │
         └─ ✏️ がついている
                  │
                  ▼
             [スレッドのコメントを確認して修正]
```

### フロー2: テーマ提案

```
[GitHub Actions: 毎日 8:00]
         │
         ▼
[Claude API: テーマ3案を生成]
         │
         ▼
[Slack: テーマ一覧を投稿]
         │ リアクション: 1️⃣ 2️⃣ 3️⃣ 🔄 ⏸️
         │
    （人間がリアクションするまで待機）
         │
         ▼
[GitHub Actions: 毎時チェック]
         │
         ├─ 1️⃣/2️⃣/3️⃣ が選択された
         │        │
         │        ▼
         │   [state.json を更新]
         │   [Slack: 「テーマXを選択しました」]
         │
         └─ ⏸️ が選択された
                  │
                  ▼
             [何もしない]
```

### フロー3: 週次振り返り

```
[GitHub Actions: 毎週月曜 9:00]
         │
         ▼
[Claude API: 振り返りレポート生成]
         │ 参照: output/x_posts/post_history.md
         │ 参照: rules/ai-learnings.md
         ▼
[Slack: 振り返りレポートを投稿]
         │ リアクション: 📝 ✅ 👍
         │
         ├─ 📝 がついている
         │        │
         │        ▼
         │   [rules/ai-learnings.md に学びを追記]
         │
         └─ ✅ がついている
                  │
                  ▼
             [戦略ルールを更新]
```

---

## Slackメッセージ例

### X投稿提案

```
🐦 本日のツイート提案 (2026/04/25)

リアクションで操作してください:
✅ = 承認して投稿
❌ = 却下
✏️ = 修正が必要（スレッドにコメントしてください）

━━━━━━━━━━━━━━━━━━━━━━━━
```

```
【案1】📢 記事宣伝

ADHDの「あとでやる」は永遠に来ない...😇

だからChatGPTに外注することにした!

具体的なプロンプト5つをnoteにまとめました👍
https://note.com/xxx

📝 文字数: 89/280 ✅
💡 理由: 記事宣伝 + 共感を誘う導入

━━━━━━━━━━━━━━━━━━━━━━━━

✅ ❌ ✏️
```

### テーマ提案

```
🎯 新しい記事テーマを提案します (2026/04/25)

リアクションで選択してください:
1️⃣ 2️⃣ 3️⃣ = テーマを選択
🔄 = 別の提案を見る
⏸️ = 今日はスキップ

━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Claude × ADHD仕事術
👥 ターゲット: Claude未経験のADHD当事者
💎 価値: 初期設定から使い方まで完全ガイド
🔥 需要: 高 | 🌟 競合: 少
💡 Claudeの認知度が上がっており、ADHD向けガイドが少ない

2️⃣ AI習慣化コーチ
👥 ターゲット: 三日坊主に悩むADHD
💎 価値: AIで習慣を維持する仕組み
📈 需要: 中 | 🎯 競合: 中

3️⃣ タスク管理プロンプト集
👥 ターゲット: タスク管理ツールが続かない人
💎 価値: すぐ使えるプロンプト10選
🔥 需要: 高 | ⚔️ 競合: 多

━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ 2️⃣ 3️⃣ 🔄 ⏸️
```

---

## 技術スタック

| コンポーネント | 技術 | 備考 |
|--------------|------|------|
| スケジューラー | GitHub Actions | cron式で定期実行 |
| AI実行 | Claude API | claude-sonnet |
| Slack連携 | slack-sdk (Python) | Bot Token使用 |
| X投稿 | tweepy (X API v2) | 既存のロジック流用 |
| 状態管理 | リポジトリ内JSON | output/に保存 |

---

## 必要な設定

### GitHub Secrets

リポジトリの Settings → Secrets and variables → Actions で設定:

```
ANTHROPIC_API_KEY    # Claude API キー
SLACK_BOT_TOKEN      # Slack Bot Token (xoxb-xxx)
SLACK_CHANNEL        # 投稿先チャンネル (#note-business)
X_API_KEY            # X API キー
X_API_KEY_SECRET     # X API シークレット
X_ACCESS_TOKEN       # X アクセストークン
X_ACCESS_TOKEN_SECRET # X アクセストークンシークレット
```

### Slack App 設定

1. https://api.slack.com/apps でアプリ作成
2. Bot Token Scopes:
   - `chat:write`
   - `reactions:read`
   - `reactions:write`
   - `channels:history`
3. アプリをワークスペースにインストール
4. Bot Token をコピーして GitHub Secrets に設定

---

## 実装ステップ

### Step 1: GitHub Actions ✅
- [x] daily-xpost.yml
- [x] daily-trend.yml
- [x] weekly-reflection.yml
- [x] check-reactions.yml

### Step 2: スクリプト ✅
- [x] generate_tweets.py
- [x] generate_themes.py
- [x] generate_reflection.py
- [x] post_to_slack.py
- [x] post_themes_to_slack.py
- [x] post_reflection_to_slack.py
- [x] check_slack_reactions.py

### Step 3: デプロイ ⏳
- [ ] Slack App 作成
- [ ] GitHub Secrets 設定
- [ ] 手動実行でテスト
- [ ] 本番運用開始

---

## 費用

| サービス | 費用 |
|---------|------|
| GitHub Actions | **無料**（2,000分/月） |
| Claude API | ~$1-5/月（使用量による） |
| X API | ~$0.10/月（10投稿 × $0.01） |
| **合計** | **~$1-6/月** |

---

## メリット

1. **AWS不要**: GitHub Actionsだけで完結
2. **無料枠で運用可能**: GitHub Actions 2,000分/月
3. **シンプル**: Lambda/API Gatewayの設定不要
4. **GitHubで完結**: コード・実行・ログすべてGitHub内

## 制限事項

1. **リアルタイム性なし**: ボタン押下から最大1時間の遅延
2. **複雑な対話不可**: 修正はスレッドコメントで対応

---

## 次のアクション

1. **Slack App 作成**: https://api.slack.com/apps
2. **GitHub Secrets 設定**: リポジトリ Settings → Secrets
3. **手動実行テスト**: Actions → daily-xpost → Run workflow
4. **本番運用開始**
