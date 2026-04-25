"""
X投稿実行ハンドラー
既存のpost_tweet.pyを呼び出す
"""

import os
import sys
import json
from datetime import datetime

# 既存のpost_tweet.pyのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '.claude', 'skills', 'x-post'))

def execute_x_post(text: str, quote_id: str = None, reply_to: str = None) -> dict:
    """
    X (Twitter) に投稿する

    Args:
        text: ツイート本文
        quote_id: 引用するツイートID（オプション）
        reply_to: リプライ先のツイートID（オプション）

    Returns:
        dict: {success: bool, tweet_id: str, tweet_url: str, error: str}
    """
    try:
        import tweepy
        from dotenv import load_dotenv

        # 環境変数を読み込む
        env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
        load_dotenv(env_path)

        # API認証
        api_key = os.getenv('X_API_KEY')
        api_key_secret = os.getenv('X_API_KEY_SECRET')
        access_token = os.getenv('X_ACCESS_TOKEN')
        access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')

        if not all([api_key, api_key_secret, access_token, access_token_secret]):
            return {
                "success": False,
                "error": "X API認証情報が不足しています"
            }

        # クライアント作成
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_key_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        # 文字数チェック（Twitter換算）
        twitter_count = calculate_twitter_length(text)
        if twitter_count > 280:
            return {
                "success": False,
                "error": f"文字数超過: {twitter_count}文字（上限280）"
            }

        # 投稿実行
        response = client.create_tweet(
            text=text,
            in_reply_to_tweet_id=reply_to,
            quote_tweet_id=quote_id
        )

        tweet_id = response.data['id']
        tweet_url = f"https://x.com/i/status/{tweet_id}"

        # 投稿履歴に記録
        log_post_to_history(text, tweet_url, quote_id)

        return {
            "success": True,
            "tweet_id": tweet_id,
            "tweet_url": tweet_url,
            "text": text
        }

    except tweepy.errors.TweepyException as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"予期せぬエラー: {str(e)}"
        }


def calculate_twitter_length(text: str) -> int:
    """
    Twitter換算の文字数を計算

    - 半角英数: 1文字
    - 日本語/絵文字: 2文字
    - URL: 23文字固定
    """
    import re

    # URLを抽出して23文字としてカウント
    url_pattern = r'https?://\S+'
    urls = re.findall(url_pattern, text)
    text_without_urls = re.sub(url_pattern, '', text)

    count = 0
    for char in text_without_urls:
        if ord(char) <= 0x7F:  # ASCII
            count += 1
        else:  # 日本語・絵文字など
            count += 2

    # URLは1つ23文字
    count += len(urls) * 23

    return count


def log_post_to_history(text: str, tweet_url: str, quote_id: str = None):
    """投稿履歴を記録"""
    history_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..',
        'output', 'x_posts', 'post_history.md'
    )

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    post_type = "引用RT" if quote_id else "単発"

    entry = f"""
### {timestamp}
- タイプ: {post_type}
- 本文: {text}
- URL: {tweet_url}
- ステータス: 成功（Slack経由）

---
"""

    try:
        with open(history_path, 'a', encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass  # ログ記録失敗は無視


def send_tweet_review_to_slack(slack_client, channel: str, tweet_text: str, quote_id: str = None):
    """
    Slackにツイートレビュー依頼を送信

    Args:
        slack_client: Slack WebClient
        channel: 送信先チャンネル
        tweet_text: ツイート本文
        quote_id: 引用元ツイートID（オプション）
    """
    char_count = calculate_twitter_length(tweet_text)
    char_status = "✅" if char_count <= 280 else "❌"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🐦 ツイート投稿の確認"
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
                {
                    "type": "mrkdwn",
                    "text": f"📝 文字数: {char_count}/280 {char_status}"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ このまま投稿"},
                    "style": "primary",
                    "action_id": "approve_tweet",
                    "value": json.dumps({"text": tweet_text, "quote_id": quote_id})
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✏️ 修正する"},
                    "action_id": "edit_tweet",
                    "value": json.dumps({"text": tweet_text, "quote_id": quote_id})
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ キャンセル"},
                    "style": "danger",
                    "action_id": "reject_tweet",
                    "value": json.dumps({"text": tweet_text})
                }
            ]
        }
    ]

    if quote_id:
        blocks.insert(2, {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"↩️ 引用元: https://x.com/i/status/{quote_id}"}
            ]
        })

    slack_client.chat_postMessage(
        channel=channel,
        text=f"ツイート確認: {tweet_text[:50]}...",
        blocks=blocks
    )
