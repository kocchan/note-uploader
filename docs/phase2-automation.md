# Phase 2: 自動化アーキテクチャ設計

## 概要

**Claude for Slack** + GitHub Actions を使って、**エージェントが自律的に動作**し、人間レビューをSlack上で完結させる。

**特徴:**
- **Claude for Slack** で会話・提案・判断を処理（Max プラン内、追加料金なし）
- GitHub Actions はコード実行（X投稿、ファイル操作）のみ担当
- Cloudflare Workers 不要（Claude for Slack が直接応答）
- `.claude/agents/` のエージェント定義をプロンプトとして活用
- 人間への質問は Slack 上で直接対話
- **パブリックリポジトリで GitHub Actions 無制限・無料**
- AWS不要、極めてシンプルな構成

---

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                         Slack                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ #note-business チャンネル                                  │  │
│  │                                                           │  │
│  │ 【会話・提案】（Claude for Slack が即座に応答）            │  │
│  │ ・@Claude ツイート案を3つ考えて → 即座に提案               │  │
│  │ ・@Claude この記事のタイトル案は？ → 即座に回答            │  │
│  │ ・@Claude トレンド分析して → 分析結果を返信                │  │
│  │                                                           │  │
│  │ 【コード実行が必要な場合】                                 │  │
│  │ ・「これでツイートして」→ 人間が /x-post コマンド実行      │  │
│  │ ・定期実行 → GitHub Actions が自動起動                     │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│         ┌────────────────────┴────────────────────┐              │
│         ▼                                         ▼              │
│  ┌─────────────────────┐              ┌────────────────────┐    │
│  │ Claude for Slack    │              │ Slack Workflow     │    │
│  │ (Max プラン内)       │              │ Builder (optional) │    │
│  │                     │              │                    │    │
│  │ ・会話応答          │              │ ・定期リマインド   │    │
│  │ ・アイデア提案      │              │ ・ボタン付き投稿   │    │
│  │ ・分析・レビュー    │              │                    │    │
│  │ ・戦略相談          │              │                    │    │
│  └─────────────────────┘              └────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ 実際の投稿が必要な時のみ
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions                                │
│                                                                  │
│  【トリガー】                                                    │
│  ・workflow_dispatch: 手動実行（Slack から人間がトリガー）       │
│  ・schedule: cron（定期レポート生成など）                        │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Claude Code CLI（コード実行のみ）              │  │
│  │                                                            │  │
│  │  実行内容:                                                  │  │
│  │  ・X API でツイート投稿                                     │  │
│  │  ・ファイル操作（output/ への保存）                         │  │
│  │  ・Git コミット・プッシュ                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│      ┌────────────────────┼────────────────────┐                │
│      ▼                    ▼                    ▼                │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────┐         │
│  │ rules/      │  │ output/         │  │ X API       │         │
│  │             │  │                 │  │ (tweepy)    │         │
│  │ ルール参照  │  │ 結果を保存      │  │             │         │
│  │             │  │                 │  │ ツイート    │         │
│  │             │  │                 │  │ 投稿        │         │
│  └─────────────┘  └─────────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Claude for Slack の仕組み

**Claude for Slack** は Anthropic が提供する公式 Slack 連携。Max プランに含まれるため追加の API 料金不要。

### できること

| 機能 | 説明 |
|------|------|
| メンション応答 | `@Claude` でメンションすると即座に応答 |
| スレッド会話 | スレッド内で文脈を保持した会話 |
| ファイル分析 | 添付ファイルの内容を読んで分析 |
| 長文生成 | 記事の下書き、ツイート案の作成 |

### メリット

1. **追加料金なし**: Max プランに含まれる
2. **即時応答**: API 経由より高速（Webhook 不要）
3. **シンプル**: Cloudflare Workers、MCP 設定が不要
4. **会話的**: 自然な対話で要望を伝えられる

### 制限事項

1. **外部 API 呼び出し不可**: X への投稿などは GitHub Actions が必要
2. **ファイル書き込み不可**: output/ への保存は GitHub Actions が必要
3. **定期実行不可**: cron 実行は GitHub Actions で行う

---

## 役割分担

| 処理 | 担当 | 理由 |
|------|------|------|
| ツイート案の作成 | Claude for Slack | 会話で即座に |
| 記事タイトル提案 | Claude for Slack | 会話で即座に |
| トレンド分析 | Claude for Slack | Web検索可能 |
| 戦略相談 | Claude for Slack | 対話が適切 |
| **X への投稿** | GitHub Actions | API 呼び出し必要 |
| **ファイル保存** | GitHub Actions | リポジトリ操作必要 |
| **定期レポート** | GitHub Actions | cron 必要 |

---

## 運用方法

### Claude for Slack での対話例

```
人間: @Claude ADHDの先延ばし対策について、ツイート案を3つ考えて

Claude: ADHDの先延ばし対策ツイート案です：

【案1】
ADHDの「あとでやる」は意志の問題じゃない。
脳の報酬系が「今すぐのご褒美」を強く求めるから。
ChatGPTに「5分で終わる最初の一歩」を聞くだけで、
脳を騙してスタートできる。

【案2】
...

人間: 案1でいこう。投稿して

Claude: 了解です！ただ、私は直接 X に投稿する機能を持っていません。
以下のツイート文をコピーして、X から投稿するか、
GitHub Actions の /x-post ワークフローを実行してください：

「ADHDの「あとでやる」は意志の問題じゃない...」
```

### GitHub Actions が必要なケース

| ケース | 実行方法 |
|--------|---------|
| X へのツイート投稿 | `workflow_dispatch` で手動実行 |
| 定期ツイート提案 | `schedule` で自動実行 → Slack に通知 |
| 振り返りレポート生成 | `schedule` で週次実行 |

### 引き続き使用するスキル（GitHub Actions 内）

| スキル | 用途 |
|--------|------|
| `/x-post` | X (Twitter) に投稿 |
| `/x-promotion` | 記事宣伝ツイート作成 |
| `/reflection` | 振り返り・学習 |

---

## ディレクトリ構成

```
312_note/
├── .claude/
│   ├── agents/                   # エージェント定義（参考用プロンプト）
│   │   ├── x-manager.md          # X運用の指示書
│   │   ├── strategy-planner.md   # 戦略立案の指示書
│   │   ├── note-writer.md        # 記事執筆の指示書
│   │   └── note-business.md      # 全体管理の指示書
│   └── skills/
│       ├── x-post/               # X投稿スキル（GitHub Actions用）
│       ├── x-promotion/          # 記事宣伝スキル
│       └── ...
├── .github/
│   └── workflows/
│       ├── x-post.yml            # X投稿（手動トリガー）
│       ├── daily-reminder.yml    # 毎日12:00: Slack にリマインド
│       └── weekly-reflection.yml # 毎週月曜: 振り返りレポート
├── rules/
│   ├── x-posting-rules.md        # X投稿ルール
│   ├── strategy-rules.md         # 戦略ルール
│   └── ai-learnings.md           # AI学習ログ
└── output/
    └── x_posts/                  # 投稿履歴
```

**削除したもの:**
- `cloudflare/` - Claude for Slack により不要
- `mcp.json` - Slack MCP 不要
- `slack-command.yml` / `slack-reaction.yml` - Claude for Slack が直接応答

---

## GitHub Actions ワークフロー

| ワークフロー | トリガー | 処理内容 |
|------------|---------|---------|
| `x-post.yml` | workflow_dispatch（手動） | 承認済みツイートを X に投稿 |
| `daily-reminder.yml` | 毎日 12:00 JST | Slack に「@Claude でツイート案を相談してね」と通知 |
| `weekly-reflection.yml` | 毎週月曜 9:00 JST | 振り返りレポートを生成して Slack に通知 |

**Note:** 以前の `slack-command.yml` / `slack-reaction.yml` は Claude for Slack が代替

---

## 必要な設定

### 1. Claude for Slack の導入

1. Slack ワークスペースに Claude for Slack をインストール
   - https://slack.com/apps/A04KGS7N9A8-claude
2. #note-business チャンネルに Claude を招待
   ```
   /invite @Claude
   ```
3. Max プランで利用（追加料金なし）

### 2. GitHub Secrets

リポジトリの Settings → Secrets and variables → Actions で設定:

```
ANTHROPIC_API_KEY    # Claude API キー（GitHub Actions での実行用）
SLACK_WEBHOOK_URL    # Slack Incoming Webhook URL（通知用）
X_API_KEY            # X API キー
X_API_KEY_SECRET     # X API シークレット
X_ACCESS_TOKEN       # X アクセストークン
X_ACCESS_TOKEN_SECRET # X アクセストークンシークレット
```

**削除した設定:**
- `SLACK_BOT_TOKEN` - Claude for Slack が代替
- `SLACK_TEAM_ID` - 不要
- `GITHUB_PAT` - repository_dispatch 不要

### 3. Slack Incoming Webhook（通知用）

GitHub Actions から Slack に通知を送るための設定:

1. https://api.slack.com/apps → 新規作成 or 既存アプリ
2. **Incoming Webhooks** → 有効化
3. **Add New Webhook to Workspace** → #note-business を選択
4. Webhook URL を `SLACK_WEBHOOK_URL` に設定

---

## 自動化フロー

### フロー1: ツイート案の相談（Claude for Slack）

```
┌─────────────────────────────────────────────┐
│ Slack: #note-business                        │
│                                              │
│ 人間: @Claude 今日のツイート案を3つ考えて     │
│                                              │
│ Claude: ADHDツイート案です：                  │
│ 【案1】ADHDの「あとでやる」は意志の問題じゃ...│
│ 【案2】...                                   │
│ 【案3】...                                   │
│                                              │
│ 人間: 案1でいこう                             │
│                                              │
│ Claude: 了解です！以下をコピーして投稿するか、│
│ GitHub Actions で x-post を実行してください  │
└─────────────────────────────────────────────┘
```

**所要時間**: 即座（Claude for Slack が直接応答）

### フロー2: X への投稿（GitHub Actions）

```
┌─────────────────────────────────────┐
│ 人間: GitHub で x-post.yml を実行    │
│ （または Slack から手動トリガー）    │
└──────────────────┬──────────────────┘
                   │
                   ▼
[GitHub Actions: x-post.yml]
                   │
                   ▼
[Claude Code CLI]
  1. 入力されたツイート文を取得
  2. /x-post スキルで X に投稿
  3. Slack Webhook で結果を通知
                   │
                   ▼
┌─────────────────────────────────────┐
│ Slack: #note-business               │
│ ✅ ツイートを投稿しました            │
│ https://x.com/xxx/status/123...     │
└─────────────────────────────────────┘
```

### フロー3: 定期リマインド（GitHub Actions）

```
[GitHub Actions: 毎日 12:00]
         │
         ▼
[Slack Webhook で通知]
         │
         ▼
┌─────────────────────────────────────────────┐
│ Slack: #note-business                        │
│ 📝 今日のツイートを考えましょう！             │
│ @Claude に相談してツイート案を作成してね      │
└─────────────────────────────────────────────┘
         │
         ▼
[人間が @Claude に話しかける → フロー1へ]
```

---

## 技術スタック

| コンポーネント | 技術 | 備考 |
|--------------|------|------|
| 会話・提案 | **Claude for Slack** | Max プラン内、追加料金なし |
| 定期通知 | GitHub Actions | cron + Slack Webhook |
| コード実行 | Claude Code CLI | X投稿、ファイル操作のみ |
| X投稿 | tweepy (X API v2) | /x-post スキル |
| 状態管理 | リポジトリ内ファイル | output/に保存 |

**削除したもの:**
- Cloudflare Workers（Claude for Slack により不要）
- Slack MCP（Claude for Slack により不要）

---

## 実装ステップ

### Step 1: Claude for Slack 導入 ⏳
- [ ] Slack に Claude をインストール
- [ ] #note-business チャンネルに招待
- [ ] テスト会話

### Step 2: GitHub Actions 更新 ⏳
- [ ] x-post.yml 作成（手動トリガー）
- [ ] daily-reminder.yml 作成（定期通知）
- [ ] SLACK_WEBHOOK_URL 設定

### Step 3: テスト ⏳
- [ ] Claude for Slack との会話テスト
- [ ] X 投稿テスト
- [ ] 定期通知テスト

---

## 費用

| サービス | 費用 |
|---------|------|
| GitHub Actions | **無料**（パブリックリポジトリ無制限） |
| Claude for Slack | **無料**（Max プラン内） |
| Claude API（GitHub Actions用） | ~$1-3/月（投稿時のみ） |
| X API | ~$0.10/月（10投稿 × $0.01） |
| **合計** | **~$1-4/月** |

**コスト削減効果:** 従来 ~$5-16/月 → **~$1-4/月**（約75%削減）

---

## メリット

1. **超低コスト**: Claude for Slack は Max プラン内、追加料金なし
2. **即時応答**: Webhook 経由不要、Claude が直接 Slack で応答
3. **シンプル**: Cloudflare Workers、MCP 設定が不要
4. **会話的**: 自然な対話でアイデア出しや相談ができる
5. **柔軟性**: プロンプト次第で様々なタスクに対応

## 制限事項

1. **外部 API 呼び出し不可**: X 投稿は GitHub Actions が必要
2. **ファイル操作不可**: リポジトリへの保存は GitHub Actions が必要
3. **自動実行不可**: 定期実行は GitHub Actions cron で通知のみ

## 旧アーキテクチャとの比較

| 項目 | 旧（Slack App + API） | 新（Claude for Slack） |
|------|----------------------|------------------------|
| 月額コスト | ~$5-16 | ~$1-4 |
| 設定の複雑さ | 高（Workers, MCP） | 低（招待のみ） |
| 応答速度 | 1-3秒 | 即時 |
| 外部 API 実行 | ✅ 可能 | ❌ 不可（Actions経由） |
| 定期実行 | ✅ 自動 | ⚠️ 通知のみ |

---

## 次のアクション

1. **Claude for Slack をインストール**
2. **#note-business に Claude を招待**
3. **テスト会話で動作確認**
4. **x-post.yml ワークフロー作成**
5. **daily-reminder.yml ワークフロー作成**
