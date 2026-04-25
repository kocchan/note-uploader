"""
毎日のX投稿提案
定期実行: 毎日 12:00 JST
"""

import os
import json
import logging
from slack_sdk import WebClient

logger = logging.getLogger(__name__)


def handler(event, context):
    """
    Lambda ハンドラー
    1. Claude API でツイート案を生成
    2. Slackに承認依頼を送信
    """
    logger.info("Daily X post suggestion started")

    slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel = os.environ.get("SLACK_CHANNEL", "#note-business")

    try:
        # ツイート案を生成
        tweet_suggestions = generate_tweet_suggestions()

        if not tweet_suggestions:
            logger.info("No tweet suggestions generated")
            return {"statusCode": 200, "body": "No suggestions"}

        # 各ツイート案をSlackに送信
        for suggestion in tweet_suggestions:
            send_tweet_review_request(slack_client, channel, suggestion)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Sent {len(tweet_suggestions)} tweet suggestions"})
        }

    except Exception as e:
        logger.error(f"Error in daily X post: {str(e)}")
        # エラーをSlackに通知
        slack_client.chat_postMessage(
            channel=channel,
            text=f"❌ X投稿提案でエラーが発生しました: {str(e)}"
        )
        return {"statusCode": 500, "body": str(e)}


def generate_tweet_suggestions() -> list:
    """
    Claude API を使ってツイート案を生成

    Returns:
        list: ツイート案のリスト
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # X投稿ルールを読み込む
    rules_path = os.path.join(os.path.dirname(__file__), '..', '..', 'rules', 'x-posting-rules.md')
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            posting_rules = f.read()
    except:
        posting_rules = ""

    # 最新の記事情報を取得
    state_path = os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'state.json')
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except:
        state = {}

    prompt = f"""あなたはADHD向けnote有料記事ビジネスのX運用担当です。

## 投稿ルール
{posting_rules}

## 現在の状況
{json.dumps(state, ensure_ascii=False, indent=2)}

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
    "type": "promotion" | "empathy" | "value",
    "text": "ツイート本文（140文字以内推奨）",
    "reason": "このツイートを提案する理由"
  }}
]
```

日本語のツイートを作成し、ツイート文体ルールに従ってください。
「!」「...」「絵文字」を使い、口語的に書いてください。
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
        suggestions = json.loads(json_match.group())
        return suggestions

    return []


def send_tweet_review_request(slack_client, channel: str, suggestion: dict):
    """Slackにツイート承認依頼を送信"""
    from src.slack.handlers.x_post_handler import calculate_twitter_length

    tweet_text = suggestion["text"]
    char_count = calculate_twitter_length(tweet_text)
    char_status = "✅" if char_count <= 280 else "❌"

    type_emoji = {
        "promotion": "📢",
        "empathy": "💭",
        "value": "💡"
    }.get(suggestion.get("type", ""), "🐦")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{type_emoji} ツイート投稿の提案"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{tweet_text}```"
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"📝 文字数: {char_count}/280 {char_status}"},
                {"type": "mrkdwn", "text": f"💡 理由: {suggestion.get('reason', 'N/A')}"}
            ]
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ このまま投稿"},
                    "style": "primary",
                    "action_id": "approve_tweet",
                    "value": json.dumps({"text": tweet_text, "quote_id": None})
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✏️ 修正する"},
                    "action_id": "edit_tweet",
                    "value": json.dumps({"text": tweet_text, "quote_id": None})
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ スキップ"},
                    "style": "danger",
                    "action_id": "reject_tweet",
                    "value": json.dumps({"text": tweet_text})
                }
            ]
        }
    ]

    slack_client.chat_postMessage(
        channel=channel,
        text=f"ツイート提案: {tweet_text[:50]}...",
        blocks=blocks
    )
