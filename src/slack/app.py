"""
Slack Bolt App for note-business automation
AWS Lambda 対応版
"""

import os
import json
import logging
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Slack App初期化
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True  # Lambda用: 3秒以内にレスポンスを返す
)


# ==========================================
# X投稿レビューフロー
# ==========================================

@app.action("approve_tweet")
def handle_approve_tweet(ack, body, client, logger):
    """ツイート承認ボタンが押されたとき"""
    ack()

    # メタデータから投稿内容を取得
    tweet_data = json.loads(body["actions"][0]["value"])
    tweet_text = tweet_data["text"]
    quote_id = tweet_data.get("quote_id")

    # 承認メッセージを更新
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text=f"✅ 投稿を承認しました: {tweet_text[:50]}...",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *投稿承認済み*\n\n```{tweet_text}```"
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "🔄 投稿処理中..."}
                ]
            }
        ]
    )

    # X投稿実行（別スレッドまたはStep Functions）
    # ここでpost_tweet.pyを呼び出す or GitHub Actions をトリガー
    from src.slack.handlers.x_post_handler import execute_x_post
    result = execute_x_post(tweet_text, quote_id)

    # 結果を更新
    if result["success"]:
        client.chat_update(
            channel=body["channel"]["id"],
            ts=body["message"]["ts"],
            text=f"✅ 投稿完了: {result['tweet_url']}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *投稿完了*\n\n```{tweet_text}```\n\n<{result['tweet_url']}|ツイートを見る>"
                    }
                }
            ]
        )
    else:
        client.chat_postMessage(
            channel=body["channel"]["id"],
            text=f"❌ 投稿失敗: {result['error']}"
        )


@app.action("edit_tweet")
def handle_edit_tweet(ack, body, client):
    """ツイート修正ボタンが押されたとき"""
    ack()

    tweet_data = json.loads(body["actions"][0]["value"])

    # 修正用モーダルを表示
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "edit_tweet_modal",
            "private_metadata": json.dumps({
                "channel_id": body["channel"]["id"],
                "message_ts": body["message"]["ts"],
                "quote_id": tweet_data.get("quote_id")
            }),
            "title": {"type": "plain_text", "text": "ツイート修正"},
            "submit": {"type": "plain_text", "text": "この内容で投稿"},
            "close": {"type": "plain_text", "text": "キャンセル"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "tweet_input",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "tweet_text",
                        "multiline": True,
                        "initial_value": tweet_data["text"],
                        "max_length": 280
                    },
                    "label": {"type": "plain_text", "text": "ツイート内容"}
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "💡 日本語は1文字=2カウント。140文字以内が安全"}
                    ]
                }
            ]
        }
    )


@app.view("edit_tweet_modal")
def handle_edit_tweet_submit(ack, body, client, view):
    """修正モーダル送信時"""
    ack()

    metadata = json.loads(view["private_metadata"])
    new_text = view["state"]["values"]["tweet_input"]["tweet_text"]["value"]

    # 元のメッセージを更新
    client.chat_update(
        channel=metadata["channel_id"],
        ts=metadata["message_ts"],
        text=f"✏️ 修正版を投稿中: {new_text[:50]}...",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✏️ *修正版を投稿中*\n\n```{new_text}```"
                }
            }
        ]
    )

    # X投稿実行
    from src.slack.handlers.x_post_handler import execute_x_post
    result = execute_x_post(new_text, metadata.get("quote_id"))

    if result["success"]:
        client.chat_update(
            channel=metadata["channel_id"],
            ts=metadata["message_ts"],
            text=f"✅ 投稿完了: {result['tweet_url']}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *投稿完了*\n\n```{new_text}```\n\n<{result['tweet_url']}|ツイートを見る>"
                    }
                }
            ]
        )


@app.action("reject_tweet")
def handle_reject_tweet(ack, body, client):
    """ツイート却下ボタンが押されたとき"""
    ack()

    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="❌ 投稿をキャンセルしました",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "❌ *投稿キャンセル*\n\nこのツイートは投稿されませんでした。"
                }
            }
        ]
    )


# ==========================================
# スラッシュコマンド
# ==========================================

@app.command("/note-status")
def handle_status_command(ack, respond, command):
    """現在の状態を表示"""
    ack()

    # state.jsonを読み込む
    try:
        with open("output/state.json", "r") as f:
            state = json.load(f)

        respond({
            "response_type": "in_channel",
            "text": f"📊 現在の状態\n\nフェーズ: {state.get('current_phase', 'N/A')}\nテーマ: {state.get('selected_theme', 'N/A')}"
        })
    except Exception as e:
        respond(f"❌ 状態取得エラー: {str(e)}")


@app.command("/x-post-now")
def handle_x_post_command(ack, respond, command):
    """手動でX投稿レビューを開始"""
    ack()
    respond("🔄 X投稿案を生成中...")

    # Claude API でツイート案を生成
    # → 生成後、レビュー用メッセージを送信


# ==========================================
# Lambda ハンドラー
# ==========================================

def lambda_handler(event, context):
    """AWS Lambda エントリーポイント"""
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)


# ローカル実行用
if __name__ == "__main__":
    app.start(port=3000)
