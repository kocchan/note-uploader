#!/usr/bin/env python3
"""
テーマ案をSlackに投稿
"""

import os
import sys
import json
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def post_themes_to_slack(themes: list):
    """テーマ案をSlackに投稿"""
    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel = os.environ.get("SLACK_CHANNEL", "#note-business")

    today = datetime.now().strftime("%Y/%m/%d")

    demand_emoji = {"高": "🔥", "中": "📈", "低": "📉"}
    comp_emoji = {"多": "⚔️", "中": "🎯", "少": "🌟"}

    # テーマ一覧を構築
    theme_blocks = []
    for theme in themes:
        d_emoji = demand_emoji.get(theme.get("demand", ""), "")
        c_emoji = comp_emoji.get(theme.get("competition", ""), "")

        theme_blocks.append(f"""
*{theme['id']}️⃣ {theme['title']}*
👥 ターゲット: {theme.get('target', 'N/A')}
💎 価値: {theme.get('value', 'N/A')}
{d_emoji} 需要: {theme.get('demand', 'N/A')} | {c_emoji} 競合: {theme.get('competition', 'N/A')}
💡 {theme.get('reason', '')}
""")

    message = f"""🎯 *新しい記事テーマを提案します* ({today})

リアクションで選択してください:
1️⃣ 2️⃣ 3️⃣ = テーマを選択
🔄 = 別の提案を見る
⏸️ = 今日はスキップ

━━━━━━━━━━━━━━━━━━━━━━━━
{"".join(theme_blocks)}
━━━━━━━━━━━━━━━━━━━━━━━━"""

    try:
        response = client.chat_postMessage(
            channel=channel,
            text=message,
            mrkdwn=True
        )

        # リアクションを追加
        message_ts = response["ts"]
        for emoji in ["one", "two", "three", "arrows_counterclockwise", "double_vertical_bar"]:
            try:
                client.reactions_add(
                    channel=channel,
                    name=emoji,
                    timestamp=message_ts
                )
            except SlackApiError:
                pass

        print(f"Posted {len(themes)} theme suggestions to Slack")

        # メッセージデータを保存
        save_data = {
            "date": datetime.now().strftime("%Y%m%d"),
            "message_ts": message_ts,
            "channel": channel,
            "themes": themes
        }

        os.makedirs("output/pending_themes", exist_ok=True)
        with open(f"output/pending_themes/{save_data['date']}_slack.json", 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

    except SlackApiError as e:
        print(f"Error posting to Slack: {e.response['error']}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python post_themes_to_slack.py <themes.json>")
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        themes = json.load(f)

    if not themes:
        print("No themes to post")
        sys.exit(0)

    post_themes_to_slack(themes)


if __name__ == "__main__":
    main()
