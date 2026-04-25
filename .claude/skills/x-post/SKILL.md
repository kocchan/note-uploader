# X投稿スキル

ツイート文章を作成し、人間のレビュー後にX APIを使って投稿するスキルです。

## ルール参照（必須）

実行前に以下のファイルを読み込み、ルールに従って実行すること:
- `rules/x-posting-rules.md` - **X投稿ルール（ツイート文体を必ず守る）**

## 前提条件

### 1. X API認証情報

`.env` ファイルに以下のX API認証情報が必要:
```
X_API_KEY=your_api_key
X_API_KEY_SECRET=your_api_key_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

### 2. Python環境セットアップ（初回のみ）

```bash
# 仮想環境を作成
python3 -m venv .claude/skills/x-post/venv

# 仮想環境を有効化
source .claude/skills/x-post/venv/bin/activate

# 必要なパッケージをインストール
pip install -r .claude/skills/x-post/requirements.txt
```

## 実行手順

### 1. 投稿タイプを確認

引数で指定されたタイプに応じて処理:

| タイプ | 説明 | 参照ファイル |
|--------|------|-------------|
| `promotion` | 記事宣伝ツイート | `output/x_posts/YYYYMMDD_promotion/article_tweets.md` |
| `engagement` | 引用RT用ツイート | `output/x_posts/YYYYMMDD_engagement/quote_tweets.md` |
| `custom` | カスタムツイート | 引数で直接指定 |

### 2. ツイート案を表示

```markdown
## 投稿予定のツイート

```
[ツイート本文]
```

文字数: XXX文字

---

**このツイートを投稿しますか？**
- はい → 投稿実行
- いいえ → キャンセル
- 修正 → 修正内容を入力
```

### 3. 人間のレビューを待つ

**重要:** 必ず人間の承認を得てから投稿する。

承認パターン:
- 「OK」「はい」「投稿して」→ 投稿実行
- 「いいえ」「キャンセル」→ 中止
- 具体的な修正指示 → 修正して再度確認

### 4. X APIで投稿

人間の承認後、以下のコマンドを実行:

```bash
.claude/skills/x-post/venv/bin/python .claude/skills/x-post/post_tweet.py "ツイート本文"
```

**引用RTの場合:**
```bash
.claude/skills/x-post/venv/bin/python .claude/skills/x-post/post_tweet.py "ツイート本文" --quote TWEET_ID
```

### 5. 結果を報告

```markdown
## 投稿完了

- ステータス: 成功 / 失敗
- ツイートURL: https://x.com/xxx/status/xxx
- 投稿日時: YYYY-MM-DD HH:MM

---

次のアクション:
- 反応を確認（数時間後）
- 必要に応じてQuote RT
```

## 投稿前チェックリスト

- [ ] ツイート文体ルールに従っているか
- [ ] **Twitter換算文字数が280文字以内か**（下記参照）
- [ ] URLが正しく含まれているか（該当する場合）
- [ ] 絵文字の使いすぎがないか（1-2個まで）
- [ ] 上から目線の表現がないか

## 文字数カウントルール（重要）

Twitterの文字数カウントは単純な文字数ではない:

| 文字種 | カウント |
|--------|----------|
| 半角英数 | 1文字 |
| 日本語（ひらがな・カタカナ・漢字） | **2文字** |
| 全角記号 | **2文字** |
| 絵文字 | **2文字** |
| URL | **23文字固定**（長さに関係なく） |

**例:**
- 「こんにちは」= 10文字（5文字×2）
- 「Hello」= 5文字
- 「https://note.com/xxx」= 23文字

**目安:**
- 日本語メインのツイート: **単純文字数140文字以内**が安全
- URL含む場合: **単純文字数120文字以内**が安全

## エラー対応

| エラー | 原因 | 対処 |
|--------|------|------|
| 認証エラー | API認証情報が不正 | `.env`の認証情報を確認 |
| レート制限 | 投稿頻度が高すぎる | 15分待ってリトライ |
| 文字数超過 | 280文字を超えている | ツイートを短縮 |

## 引数

- `$ARGUMENTS`: 投稿タイプ or ツイート本文
  - `promotion` - 記事宣伝ツイートを投稿
  - `engagement` - 引用RTツイートを投稿
  - `"ツイート本文"` - 直接指定したテキストを投稿

## 使用例

```
/x-post promotion
→ 最新の記事宣伝ツイートを投稿

/x-post engagement
→ 引用RT用ツイートを投稿

/x-post "これ、僕のことかと思った...! ChatGPT使ったら先延ばしがだいぶ減った👍"
→ 直接指定したツイートを投稿
```

## 投稿履歴

投稿後、以下のファイルに記録:
`output/x_posts/post_history.md`

```markdown
## 投稿履歴

### YYYY-MM-DD HH:MM
- タイプ: promotion / engagement / custom
- 本文: [ツイート本文]
- URL: https://x.com/xxx/status/xxx
- 反応: いいねX / RTX / 引用X（後で追記）
```

## 他スキルとの連携

### /x-promotion → /x-post

```
1. /x-promotion で宣伝ツイート案を作成
2. 人間がレビュー・承認
3. /x-post promotion で投稿実行
   または
   /x-post "承認されたツイート本文" で直接投稿
```

### /x-engagement → /x-post

```
1. /x-engagement で引用RTツイート案を作成
2. 人間がレビュー・承認
3. /x-post "ツイート本文" --quote TWEET_ID で投稿実行
```

### 統合ワークフロー

```
【記事公開後のX運用】

/x-promotion → 宣伝ツイート案作成
     ↓
【人間】承認
     ↓
/x-post "案1" → 投稿
     ↓
/x-engagement → 引用RTツイート案作成
     ↓
【人間】承認
     ↓
/x-post "引用ツイート" --quote XXX → 投稿
     ↓
/reflection → 反応を分析
```

## API料金

- 従量課金: **$0.01/投稿**
- X Developer Portalでクレジット購入が必要
