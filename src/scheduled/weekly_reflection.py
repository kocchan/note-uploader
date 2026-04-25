"""
週次振り返り → 戦略更新提案
定期実行: 毎週月曜 9:00 JST
"""

import os
import json
import logging
from slack_sdk import WebClient

logger = logging.getLogger(__name__)


def handler(event, context):
    """
    Lambda ハンドラー
    1. 先週の成果を分析
    2. 学びをまとめる
    3. 戦略更新を提案
    """
    logger.info("Weekly reflection started")

    slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel = os.environ.get("SLACK_CHANNEL", "#note-business")

    try:
        # 振り返りを実行
        reflection = generate_weekly_reflection()

        # Slackに送信
        send_reflection_message(slack_client, channel, reflection)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Weekly reflection sent"})
        }

    except Exception as e:
        logger.error(f"Error in weekly reflection: {str(e)}")
        slack_client.chat_postMessage(
            channel=channel,
            text=f"❌ 週次振り返りでエラーが発生しました: {str(e)}"
        )
        return {"statusCode": 500, "body": str(e)}


def generate_weekly_reflection() -> dict:
    """
    Claude API を使って週次振り返りを生成

    Returns:
        dict: 振り返りの内容
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # 投稿履歴を読み込む
    history_path = os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'x_posts', 'post_history.md')
    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            post_history = f.read()
    except:
        post_history = "投稿履歴なし"

    # 過去の学びを読み込む
    learnings_path = os.path.join(os.path.dirname(__file__), '..', '..', 'rules', 'ai-learnings.md')
    try:
        with open(learnings_path, 'r', encoding='utf-8') as f:
            learnings = f.read()
    except:
        learnings = ""

    # 記事の状態を読み込む
    state_path = os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'state.json')
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except:
        state = {}

    prompt = f"""あなたはADHD向けnote有料記事ビジネスの振り返り担当です。

## 先週の投稿履歴
{post_history}

## 現在の状態
{json.dumps(state, ensure_ascii=False, indent=2)}

## 過去の学び
{learnings}

## タスク
先週の活動を振り返り、以下をJSON形式で出力してください:

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
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    # JSONを抽出
    content = response.content[0].text
    import re
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        reflection = json.loads(json_match.group())
        return reflection

    return {"summary": "振り返りを生成できませんでした", "achievements": [], "challenges": [], "learnings": []}


def send_reflection_message(slack_client, channel: str, reflection: dict):
    """Slackに振り返りメッセージを送信"""

    # 達成事項
    achievements_text = "\n".join([f"• {a}" for a in reflection.get("achievements", [])]) or "なし"
    challenges_text = "\n".join([f"• {c}" for c in reflection.get("challenges", [])]) or "なし"
    learnings_text = "\n".join([f"• {l}" for l in reflection.get("learnings", [])]) or "なし"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 週次振り返りレポート"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*サマリー*\n{reflection.get('summary', 'N/A')}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*✅ 達成したこと*\n{achievements_text}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*⚠️ 課題*\n{challenges_text}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*💡 学び*\n{learnings_text}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🎯 来週の注力ポイント*\n{reflection.get('next_week_focus', 'N/A')}"
            }
        }
    ]

    # 戦略更新提案があれば追加
    strategy_updates = reflection.get("strategy_updates", [])
    if strategy_updates:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🔧 戦略更新の提案*"
            }
        })

        for i, update in enumerate(strategy_updates, 1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {update.get('area', '')}*\n"
                           f"現在: {update.get('current', '')}\n"
                           f"→ 提案: {update.get('proposed', '')}\n"
                           f"理由: {update.get('reason', '')}"
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ 採用"},
                    "style": "primary",
                    "action_id": f"approve_strategy_{i}",
                    "value": json.dumps(update)
                }
            })

    # アクションボタン
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "📝 学びをルールに追記"},
                "action_id": "save_learnings",
                "value": json.dumps(reflection.get("learnings", []))
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "👍 確認済み"},
                "action_id": "acknowledge_reflection"
            }
        ]
    })

    slack_client.chat_postMessage(
        channel=channel,
        text="週次振り返りレポートが届きました",
        blocks=blocks
    )
