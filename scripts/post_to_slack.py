#!/usr/bin/env python3
"""
ツイート案をSlackに投稿
リアクションで承認/却下を受け付ける
"""

import os
import sys
import json
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def calculate_twitter_length(text: str) -> int:
    """Twitter換算の文字数を計算"""
    import re
    url_pattern = r'https?://\S+'
    urls = re.findall(url_pattern, text)
    text_without_urls = re.sub(url_pattern, '', text)

    count = 0
    for char in text_without_urls:
        if ord(char) <= 0x7F:
            count += 1
        else:
            count += 2

    count += len(urls) * 23
    return count


def post_tweets_to_slack(tweets: list):
    """ツイート案をSlackに投稿"""
    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel = os.environ.get("SLACK_CHANNEL", "#note-business")

    today = datetime.now().strftime("%Y/%m/%d")

    # ヘッダーメッセージ
    header_text = f"""🐦 *本日のツイート提案* ({today})

リアクションで操作してください:
✅ = 承認して投稿
❌ = 却下
✏️ = 修正が必要（スレッドにコメントしてください）

━━━━━━━━━━━━━━━━━━━━━━━━"""

    try:
        header_response = client.chat_postMessage(
            channel=channel,
            text=header_text,
            mrkdwn=True
        )
        thread_ts = header_response["ts"]

        # 各ツイート案を投稿
        message_data = []
        for tweet in tweets:
            char_count = calculate_twitter_length(tweet["text"])
            char_status = "✅" if char_count <= 280 else "❌"

            type_emoji = {
                "promotion": "📢 記事宣伝",
                "empathy": "💭 共感",
                "value": "💡 価値提供"
            }.get(tweet.get("type", ""), "🐦")

            message = f"""*【案{tweet['id']}】{type_emoji}*

```
{tweet['text']}
```

📝 文字数: {char_count}/280 {char_status}
💡 理由: {tweet.get('reason', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━"""

            response = client.chat_postMessage(
                channel=channel,
                text=message,
                thread_ts=thread_ts,
                mrkdwn=True
            )

            # リアクションを追加（ユーザーが押しやすいように）
            message_ts = response["ts"]
            for emoji in ["white_check_mark", "x", "pencil2"]:
                try:
                    client.reactions_add(
                        channel=channel,
                        name=emoji,
                        timestamp=message_ts
                    )
                except SlackApiError:
                    pass

            message_data.append({
                "tweet_id": tweet["id"],
                "message_ts": message_ts,
                "thread_ts": thread_ts,
                "text": tweet["text"],
                "type": tweet.get("type", ""),
                "status": "pending"
            })

        # メッセージデータを保存（後でチェック用）
        save_message_data(message_data, thread_ts)

        print(f"Posted {len(tweets)} tweet suggestions to Slack")

    except SlackApiError as e:
        print(f"Error posting to Slack: {e.response['error']}")
        sys.exit(1)


def save_message_data(message_data: list, thread_ts: str):
    """メッセージデータを保存"""
    today = datetime.now().strftime("%Y%m%d")
    filepath = f"output/pending_tweets/{today}_slack.json"

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    data = {
        "date": today,
        "thread_ts": thread_ts,
        "channel": os.environ.get("SLACK_CHANNEL", "#note-business"),
        "messages": message_data
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print("Usage: python post_to_slack.py <tweets.json>")
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        tweets = json.load(f)

    if not tweets:
        print("No tweets to post")
        sys.exit(0)

    post_tweets_to_slack(tweets)


if __name__ == "__main__":
    main()
