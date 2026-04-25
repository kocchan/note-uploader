#!/usr/bin/env python3
"""
振り返りレポートをSlackに投稿
"""

import os
import sys
import json
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def post_reflection_to_slack(reflection: dict):
    """振り返りレポートをSlackに投稿"""
    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel = os.environ.get("SLACK_CHANNEL", "#note-business")

    today = datetime.now().strftime("%Y/%m/%d")

    achievements = "\n".join([f"• {a}" for a in reflection.get("achievements", [])]) or "なし"
    challenges = "\n".join([f"• {c}" for c in reflection.get("challenges", [])]) or "なし"
    learnings = "\n".join([f"• {l}" for l in reflection.get("learnings", [])]) or "なし"

    # 戦略更新提案
    strategy_text = ""
    for i, update in enumerate(reflection.get("strategy_updates", []), 1):
        strategy_text += f"""
*{i}. {update.get('area', '')}*
現在: {update.get('current', '')}
→ 提案: {update.get('proposed', '')}
理由: {update.get('reason', '')}
"""

    message = f"""📊 *週次振り返りレポート* ({today})

━━━━━━━━━━━━━━━━━━━━━━━━

*サマリー*
{reflection.get('summary', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━

*✅ 達成したこと*
{achievements}

*⚠️ 課題*
{challenges}

*💡 学び*
{learnings}

━━━━━━━━━━━━━━━━━━━━━━━━

*🎯 来週の注力ポイント*
{reflection.get('next_week_focus', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━

*🔧 戦略更新の提案*
{strategy_text if strategy_text else 'なし'}

━━━━━━━━━━━━━━━━━━━━━━━━

リアクションで対応:
📝 = 学びをルールに追記
✅ = 戦略更新を採用
👍 = 確認済み"""

    try:
        response = client.chat_postMessage(
            channel=channel,
            text=message,
            mrkdwn=True
        )

        # リアクションを追加
        message_ts = response["ts"]
        for emoji in ["memo", "white_check_mark", "thumbsup"]:
            try:
                client.reactions_add(
                    channel=channel,
                    name=emoji,
                    timestamp=message_ts
                )
            except SlackApiError:
                pass

        print(f"Posted reflection to Slack")

    except SlackApiError as e:
        print(f"Error posting to Slack: {e.response['error']}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python post_reflection_to_slack.py <reflection.json>")
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        reflection = json.load(f)

    post_reflection_to_slack(reflection)


if __name__ == "__main__":
    main()
