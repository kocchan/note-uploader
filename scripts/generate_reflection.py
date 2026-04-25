#!/usr/bin/env python3
"""
週次振り返りレポートを生成
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


def generate_reflection() -> dict:
    """振り返りレポートを生成"""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    post_history = load_file("output/x_posts/post_history.md")
    state = load_file("output/state.json")
    learnings = load_file("rules/ai-learnings.md")

    prompt = f"""あなたはADHD向けnote有料記事ビジネスの振り返り担当です。

## 先週の投稿履歴
{post_history}

## 現在の状態
{state}

## 過去の学び
{learnings}

## タスク
先週の活動を振り返り、以下のJSON形式で出力:

```json
{{
  "summary": "先週の活動サマリー（2-3文）",
  "achievements": ["達成したこと1", "達成したこと2"],
  "challenges": ["課題1", "課題2"],
  "learnings": ["学び1", "学び2"],
  "next_week_focus": "来週の注力ポイント",
  "strategy_updates": [
    {{
      "area": "X運用 | 記事作成 | 戦略",
      "current": "現在のやり方",
      "proposed": "提案する変更",
      "reason": "変更理由"
    }}
  ]
}}
```

JSON部分のみ出力してください。
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.content[0].text

    import re
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        reflection = json.loads(json_match.group())
        reflection["created_at"] = datetime.now().isoformat()
        return reflection

    return {
        "summary": "振り返りを生成できませんでした",
        "achievements": [],
        "challenges": [],
        "learnings": [],
        "created_at": datetime.now().isoformat()
    }


def main():
    reflection = generate_reflection()
    print(json.dumps(reflection, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
