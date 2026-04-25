#!/usr/bin/env python3
"""
Claude APIを使ってテーマ案を生成
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


def generate_themes() -> list:
    """テーマ案を生成"""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    strategy_rules = load_file("rules/strategy-rules.md")
    learnings = load_file("rules/ai-learnings.md")
    state = load_file("output/state.json")

    prompt = f"""あなたはADHD向けnote有料記事ビジネスの戦略担当です。

## 戦略ルール
{strategy_rules}

## 過去の学び
{learnings}

## 現在の状態
{state}

## タスク
次に書くべき記事テーマを3つ提案してください。

以下のJSON形式で出力:
```json
[
  {{
    "id": 1,
    "title": "テーマタイトル",
    "target": "ターゲット読者",
    "value": "提供する価値",
    "demand": "高 | 中 | 低",
    "competition": "多 | 中 | 少",
    "reason": "このテーマを提案する理由"
  }}
]
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
    json_match = re.search(r'\[[\s\S]*\]', content)
    if json_match:
        themes = json.loads(json_match.group())
        for theme in themes:
            theme["created_at"] = datetime.now().isoformat()
            theme["status"] = "pending"
        return themes

    return []


def main():
    themes = generate_themes()
    print(json.dumps(themes, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
