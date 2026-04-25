"""
毎日のトレンド収集 → テーマ提案
定期実行: 毎日 8:00 JST
"""

import os
import json
import logging
from slack_sdk import WebClient

logger = logging.getLogger(__name__)


def handler(event, context):
    """
    Lambda ハンドラー
    1. Claude API でトレンドを分析
    2. テーマを3つ提案
    3. Slackで選択を求める
    """
    logger.info("Daily trend collection started")

    slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel = os.environ.get("SLACK_CHANNEL", "#note-business")

    try:
        # トレンド分析 & テーマ提案
        themes = analyze_trends_and_suggest_themes()

        if not themes:
            slack_client.chat_postMessage(
                channel=channel,
                text="📊 本日のトレンド分析完了。新しいテーマ提案はありません。"
            )
            return {"statusCode": 200, "body": "No new themes"}

        # テーマ選択メッセージを送信
        send_theme_selection_message(slack_client, channel, themes)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Sent {len(themes)} theme suggestions"})
        }

    except Exception as e:
        logger.error(f"Error in daily trend: {str(e)}")
        slack_client.chat_postMessage(
            channel=channel,
            text=f"❌ トレンド分析でエラーが発生しました: {str(e)}"
        )
        return {"statusCode": 500, "body": str(e)}


def analyze_trends_and_suggest_themes() -> list:
    """
    Claude API を使ってトレンド分析とテーマ提案

    Returns:
        list: テーマ提案のリスト
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # 戦略ルールを読み込む
    rules_path = os.path.join(os.path.dirname(__file__), '..', '..', 'rules', 'strategy-rules.md')
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            strategy_rules = f.read()
    except:
        strategy_rules = ""

    # 過去の学びを読み込む
    learnings_path = os.path.join(os.path.dirname(__file__), '..', '..', 'rules', 'ai-learnings.md')
    try:
        with open(learnings_path, 'r', encoding='utf-8') as f:
            learnings = f.read()
    except:
        learnings = ""

    prompt = f"""あなたはADHD向けnote有料記事ビジネスの戦略担当です。

## 戦略ルール
{strategy_rules}

## 過去の学び
{learnings}

## タスク
今日の日付を考慮して、次に書くべき記事テーマを3つ提案してください。

提案の観点:
1. ADHDコミュニティでの話題性
2. AI活用（ChatGPT, Claude等）との組み合わせ
3. 1,980円の価値を提供できる具体性
4. 過去の学びを活かした改善

各テーマは以下のJSON形式で出力:
```json
[
  {{
    "title": "テーマタイトル",
    "target": "ターゲット読者",
    "value": "提供する価値",
    "demand": "高" | "中" | "低",
    "competition": "多" | "中" | "少",
    "reason": "このテーマを提案する理由"
  }}
]
```
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    # JSONを抽出
    content = response.content[0].text
    import re
    json_match = re.search(r'\[[\s\S]*\]', content)
    if json_match:
        themes = json.loads(json_match.group())
        return themes

    return []


def send_theme_selection_message(slack_client, channel: str, themes: list):
    """Slackにテーマ選択メッセージを送信"""

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🎯 新しい記事テーマを提案します"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "今日のトレンド分析に基づいて、以下のテーマを提案します。"
            }
        },
        {"type": "divider"}
    ]

    # 各テーマをブロックに追加
    for i, theme in enumerate(themes, 1):
        demand_emoji = {"高": "🔥", "中": "📈", "低": "📉"}.get(theme.get("demand", ""), "")
        comp_emoji = {"多": "⚔️", "中": "🎯", "少": "🌟"}.get(theme.get("competition", ""), "")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{i}️⃣ {theme['title']}*\n"
                       f"👥 ターゲット: {theme.get('target', 'N/A')}\n"
                       f"💎 価値: {theme.get('value', 'N/A')}\n"
                       f"{demand_emoji} 需要: {theme.get('demand', 'N/A')} | "
                       f"{comp_emoji} 競合: {theme.get('competition', 'N/A')}"
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": f"{i}️⃣ を選択"},
                "style": "primary",
                "action_id": f"select_theme_{i}",
                "value": json.dumps(theme)
            }
        })

        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"💡 {theme.get('reason', '')}"}
            ]
        })

        blocks.append({"type": "divider"})

    # 「別の提案」ボタン
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔄 別の提案を見る"},
                "action_id": "regenerate_themes"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "⏸️ 今日はスキップ"},
                "action_id": "skip_today"
            }
        ]
    })

    slack_client.chat_postMessage(
        channel=channel,
        text="新しい記事テーマの提案があります",
        blocks=blocks
    )
