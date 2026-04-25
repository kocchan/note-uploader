#!/usr/bin/env python3
"""
Slackのリアクションをチェックして、承認されたツイートを投稿
"""

import os
import sys
import json
import glob
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def post_to_x(text: str, quote_id: str = None) -> dict:
    """X (Twitter) に投稿"""
    import tweepy

    api_key = os.environ.get('X_API_KEY')
    api_key_secret = os.environ.get('X_API_KEY_SECRET')
    access_token = os.environ.get('X_ACCESS_TOKEN')
    access_token_secret = os.environ.get('X_ACCESS_TOKEN_SECRET')

    if not all([api_key, api_key_secret, access_token, access_token_secret]):
        return {"success": False, "error": "X API credentials not configured"}

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_key_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        response = client.create_tweet(
            text=text,
            quote_tweet_id=quote_id
        )

        tweet_id = response.data['id']
        tweet_url = f"https://x.com/i/status/{tweet_id}"

        return {
            "success": True,
            "tweet_id": tweet_id,
            "tweet_url": tweet_url
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def log_post(text: str, tweet_url: str, post_type: str = "auto"):
    """投稿履歴を記録"""
    history_path = "output/x_posts/post_history.md"
    os.makedirs(os.path.dirname(history_path), exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    entry = f"""
### {timestamp}
- タイプ: {post_type}
- 本文: {text}
- URL: {tweet_url}
- ステータス: 成功（GitHub Actions経由）

---
"""

    with open(history_path, 'a', encoding='utf-8') as f:
        f.write(entry)


def check_reactions():
    """保留中のツイートのリアクションをチェック"""
    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel_name = os.environ.get("SLACK_CHANNEL", "#note-business")

    # チャンネルIDを取得
    try:
        # チャンネル名からIDを取得
        response = client.conversations_list()
        channel_id = None
        for ch in response["channels"]:
            if ch["name"] == channel_name.lstrip("#"):
                channel_id = ch["id"]
                break

        if not channel_id:
            print(f"Channel {channel_name} not found")
            return

    except SlackApiError as e:
        print(f"Error getting channel: {e.response['error']}")
        return

    # 保留中のツイートデータを取得
    pending_files = glob.glob("output/pending_tweets/*_slack.json")

    for filepath in pending_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        updated = False
        for msg in data["messages"]:
            if msg["status"] != "pending":
                continue

            # リアクションを取得
            try:
                response = client.reactions_get(
                    channel=channel_id,
                    timestamp=msg["message_ts"]
                )

                reactions = response.get("message", {}).get("reactions", [])

                # リアクションをチェック
                approved = False
                rejected = False

                for reaction in reactions:
                    # Bot以外のユーザーがリアクションしたかチェック
                    if reaction["count"] > 1:  # Bot + 人間
                        if reaction["name"] == "white_check_mark":
                            approved = True
                        elif reaction["name"] == "x":
                            rejected = True

                if approved:
                    # X に投稿
                    print(f"Approved: {msg['text'][:50]}...")
                    result = post_to_x(msg["text"])

                    if result["success"]:
                        msg["status"] = "posted"
                        msg["tweet_url"] = result["tweet_url"]
                        log_post(msg["text"], result["tweet_url"], msg.get("type", "auto"))

                        # Slackに完了通知
                        client.chat_postMessage(
                            channel=channel_id,
                            thread_ts=data["thread_ts"],
                            text=f"✅ *投稿完了*\n<{result['tweet_url']}|ツイートを見る>"
                        )
                    else:
                        msg["status"] = "failed"
                        msg["error"] = result["error"]

                        client.chat_postMessage(
                            channel=channel_id,
                            thread_ts=data["thread_ts"],
                            text=f"❌ *投稿失敗*: {result['error']}"
                        )

                    updated = True

                elif rejected:
                    msg["status"] = "rejected"
                    updated = True
                    print(f"Rejected: {msg['text'][:50]}...")

                    client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=data["thread_ts"],
                        text=f"❌ 案{msg['tweet_id']}をスキップしました"
                    )

            except SlackApiError as e:
                print(f"Error getting reactions: {e.response['error']}")
                continue

        # 更新があれば保存
        if updated:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        # すべて処理済みならファイルを移動
        all_done = all(m["status"] != "pending" for m in data["messages"])
        if all_done:
            done_path = filepath.replace("pending_tweets", "done_tweets")
            os.makedirs(os.path.dirname(done_path), exist_ok=True)
            os.rename(filepath, done_path)
            print(f"All tweets processed, moved to {done_path}")


def main():
    # 日本時間の9:00-23:00のみ実行
    hour = datetime.now().hour
    if hour < 0 or hour > 14:  # UTC 0-14 = JST 9-23
        print(f"Skipping: Outside of active hours (current UTC hour: {hour})")
        return

    check_reactions()


if __name__ == "__main__":
    main()
