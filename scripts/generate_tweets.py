#!/usr/bin/env python3
"""
Claude APIを使ってツイート案を生成
"""

import os
import json
import anthropic
from datetime import datetime


def load_file(path: str) -> str:
    """ファイルを読み込む"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""


def generate_tweets() -> list:
    """ツイート案を生成"""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # ルールと状態を読み込む
    posting_rules = load_file("rules/x-posting-rules.md")
    state = load_file("output/state.json")
    learnings = load_file("rules/ai-learnings.md")

    prompt = f"""あなたはADHD向けnote有料記事ビジネスのX運用担当です。

## 投稿ルール
{posting_rules}

## 現在の状況
{state}

## 過去の学び
{learnings}

## タスク
今日投稿すべきツイートを2-3案作成してください。

以下の種類から選んで提案:
1. 記事宣伝（公開済み記事がある場合）
2. 共感ツイート（ADHD当事者として）
3. 価値提供ツイート（Tips、気づき）

各ツイートは以下のJSON形式で出力:
```json
[
  {{
    "id": 1,
    "type": "promotion | empathy | value",
    "text": "ツイート本文（140文字以内推奨）",
    "reason": "このツイートを提案する理由"
  }}
]
```

重要:
- 日本語のツイートを作成
- ツイート文体ルールに従う（「!」「...」「絵文字」を使う）
- 口語的に書く
- JSON部分のみ出力（説明文は不要）
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    # JSONを抽出
    content = response.content[0].text

    # JSON部分を抽出
    import re
    json_match = re.search(r'\[[\s\S]*\]', content)
    if json_match:
        tweets = json.loads(json_match.group())
        # 日時を追加
        for tweet in tweets:
            tweet["created_at"] = datetime.now().isoformat()
            tweet["status"] = "pending"
        return tweets

    return []


def main():
    tweets = generate_tweets()
    print(json.dumps(tweets, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
