# /slack-ask - Slack経由で人間に質問するスキル

人間への質問や提案をSlackに投稿し、リアクションで回答を待つスキル。

## 使用シーン

- ツイート案の承認を求める
- テーマ選択を求める
- 振り返りレポートを報告する
- その他、人間の判断が必要な場面

## 使い方

```
/slack-ask [メッセージタイプ] [内容]
```

### メッセージタイプ

| タイプ | 用途 | リアクション |
|--------|------|-------------|
| `tweets` | ツイート案の承認 | ✅ ❌ ✏️ |
| `themes` | テーマ選択 | 1️⃣ 2️⃣ 3️⃣ 🔄 ⏸️ |
| `report` | レポート報告 | 📝 ✅ 👍 |
| `question` | 一般的な質問 | カスタム |

## 実行手順

このスキルが呼ばれたら、以下の手順で実行してください：

### 1. 環境変数の確認

以下の環境変数が設定されていることを確認：
- `SLACK_BOT_TOKEN` - Slack Bot Token
- `SLACK_CHANNEL` - 投稿先チャンネルID

### 2. Slackに投稿

Bashツールで以下のPythonスクリプトを実行：

```bash
python3 << 'EOF'
import os
import json
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
channel = os.environ.get("SLACK_CHANNEL")

# メッセージを投稿
message = """ここに投稿するメッセージを入れる"""

response = client.chat_postMessage(
    channel=channel,
    text=message,
    mrkdwn=True
)

message_ts = response["ts"]
print(f"Posted message: {message_ts}")

# リアクションを追加（例: ツイート承認用）
for emoji in ["white_check_mark", "x", "pencil2"]:
    try:
        client.reactions_add(channel=channel, name=emoji, timestamp=message_ts)
    except SlackApiError:
        pass

# 状態を保存
save_data = {
    "type": "tweets",  # または themes, report など
    "date": datetime.now().strftime("%Y%m%d"),
    "message_ts": message_ts,
    "channel": channel,
    "content": []  # ツイート案などの内容
}

os.makedirs("output/pending", exist_ok=True)
filename = f"output/pending/{save_data['date']}_{save_data['type']}.json"
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(save_data, f, ensure_ascii=False, indent=2)

print(f"Saved to {filename}")
EOF
```

### 3. 保存形式

投稿後、以下の形式でJSONを保存：

```json
{
  "type": "tweets",
  "date": "20260425",
  "message_ts": "1234567890.123456",
  "channel": "C0B0P1C07UY",
  "content": [
    {
      "id": 1,
      "text": "ツイート本文...",
      "type": "promotion"
    }
  ]
}
```

保存先: `output/pending/{date}_{type}.json`

---

## メッセージフォーマット

### ツイート案 (tweets)

```
🐦 *本日のツイート提案* (2026/04/25)

リアクションで操作してください:
✅ = 承認して投稿
❌ = 却下
✏️ = 修正が必要（スレッドにコメントしてください）

━━━━━━━━━━━━━━━━━━━━━━━━

【案1】📢 記事宣伝

ADHDの「あとでやる」は永遠に来ない...😇

だからChatGPTに外注することにした!

具体的なプロンプト5つをnoteにまとめました👍
https://note.com/xxx

📝 文字数: 89/280 ✅
💡 理由: 記事宣伝 + 共感を誘う導入

━━━━━━━━━━━━━━━━━━━━━━━━
```

リアクション: `white_check_mark`, `x`, `pencil2`

### テーマ提案 (themes)

```
🎯 *新しい記事テーマを提案します* (2026/04/25)

リアクションで選択してください:
1️⃣ 2️⃣ 3️⃣ = テーマを選択
🔄 = 別の提案を見る
⏸️ = 今日はスキップ

━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ *Claude × ADHD仕事術*
👥 ターゲット: Claude未経験のADHD当事者
💎 価値: 初期設定から使い方まで完全ガイド
🔥 需要: 高 | 🌟 競合: 少

...
```

リアクション: `one`, `two`, `three`, `arrows_counterclockwise`, `double_vertical_bar`

### 振り返りレポート (report)

```
📊 *週次振り返りレポート* (2026/04/25)

━━━━━━━━━━━━━━━━━━━━━━━━

*サマリー*
今週は3件のツイートを投稿し...

*✅ 達成したこと*
• ...

*⚠️ 課題*
• ...

━━━━━━━━━━━━━━━━━━━━━━━━

リアクションで対応:
📝 = 学びをルールに追記
✅ = 戦略更新を採用
👍 = 確認済み
```

リアクション: `memo`, `white_check_mark`, `thumbsup`

---

## 注意事項

1. **非同期処理**: このスキルはSlackに投稿して終了。人間の回答は別のワークフロー（check-reactions）で処理される
2. **状態保存必須**: 必ず `output/pending/` にJSONを保存すること
3. **リアクション追加**: Bot自身がリアクションを追加して、人間が選びやすくする

## 関連スキル

- `/x-post` - 承認後にXに投稿
- `/reflection` - 振り返りレポート生成
