#!/usr/bin/env python
"""
X (Twitter) 投稿スクリプト
Usage: python post_tweet.py "ツイート本文"
"""

import os
import sys
import json
import re
from datetime import datetime

# tweepyがインストールされているか確認
try:
    import tweepy
except ImportError:
    print("Error: tweepyがインストールされていません")
    print("実行: pip install tweepy")
    sys.exit(1)

# python-dotenvはオプション（ローカル開発用）
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


def load_credentials():
    """環境変数からX API認証情報を読み込む

    GitHub Secrets（CI/CD環境）または .envファイル（ローカル開発）から読み込む
    """
    # まず環境変数を直接チェック（GitHub Secrets等）
    api_key = os.getenv('X_API_KEY')
    api_key_secret = os.getenv('X_API_KEY_SECRET')
    access_token = os.getenv('X_ACCESS_TOKEN')
    access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')

    # 環境変数が未設定の場合、.envファイルからロードを試みる
    if not all([api_key, api_key_secret, access_token, access_token_secret]):
        if HAS_DOTENV:
            env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
            if os.path.exists(env_path):
                load_dotenv(env_path)
                api_key = os.getenv('X_API_KEY')
                api_key_secret = os.getenv('X_API_KEY_SECRET')
                access_token = os.getenv('X_ACCESS_TOKEN')
                access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')

    # 認証情報の確認
    missing = []
    if not api_key:
        missing.append('X_API_KEY')
    if not api_key_secret:
        missing.append('X_API_KEY_SECRET')
    if not access_token:
        missing.append('X_ACCESS_TOKEN')
    if not access_token_secret:
        missing.append('X_ACCESS_TOKEN_SECRET')

    if missing:
        print(f"Error: 以下の環境変数が設定されていません: {', '.join(missing)}")
        print("GitHub Secretsまたは.envファイルで設定してください")
        sys.exit(1)

    return api_key, api_key_secret, access_token, access_token_secret


def twitter_character_count(text):
    """
    Twitterの文字数カウントルールに基づいて文字数を計算

    - 日本語・中国語・韓国語等: 1文字 = 2文字としてカウント
    - URL: 23文字固定としてカウント
    - 絵文字: 2文字としてカウント
    """
    # URLを一時的に除去してカウント
    url_pattern = r'https?://\S+'
    urls = re.findall(url_pattern, text)
    text_without_urls = re.sub(url_pattern, '', text)

    count = 0
    for char in text_without_urls:
        code_point = ord(char)
        # CJK文字（日本語、中国語、韓国語）と絵文字は2文字としてカウント
        if (0x4E00 <= code_point <= 0x9FFF or      # CJK統合漢字
            0x3040 <= code_point <= 0x309F or      # ひらがな
            0x30A0 <= code_point <= 0x30FF or      # カタカナ
            0xAC00 <= code_point <= 0xD7AF or      # ハングル
            0x3000 <= code_point <= 0x303F or      # CJK記号
            0xFF00 <= code_point <= 0xFFEF or      # 全角英数
            code_point >= 0x1F000):                 # 絵文字
            count += 2
        else:
            count += 1

    # URLは各23文字としてカウント
    count += len(urls) * 23

    return count


def create_client():
    """X API v2クライアントを作成"""
    api_key, api_key_secret, access_token, access_token_secret = load_credentials()

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_key_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    return client


def post_tweet(text, reply_to=None, quote_tweet_id=None):
    """
    ツイートを投稿する

    Args:
        text: ツイート本文
        reply_to: リプライ先のツイートID（オプション）
        quote_tweet_id: 引用するツイートID（オプション）

    Returns:
        dict: 投稿結果
    """
    # Twitter文字数チェック（日本語=2文字、URL=23文字としてカウント）
    char_count = twitter_character_count(text)
    if char_count > 280:
        print(f"Error: ツイートが280文字を超えています")
        print(f"  Twitter換算: {char_count}文字（制限: 280文字）")
        print(f"  単純文字数: {len(text)}文字")
        print(f"  超過: {char_count - 280}文字")
        sys.exit(1)

    client = create_client()

    try:
        response = client.create_tweet(
            text=text,
            in_reply_to_tweet_id=reply_to,
            quote_tweet_id=quote_tweet_id
        )

        tweet_id = response.data['id']
        tweet_url = f"https://x.com/i/status/{tweet_id}"

        result = {
            'success': True,
            'tweet_id': tweet_id,
            'tweet_url': tweet_url,
            'text': text,
            'timestamp': datetime.now().isoformat()
        }

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    except tweepy.errors.TweepyException as e:
        result = {
            'success': False,
            'error': str(e),
            'text': text,
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)


def log_post(result, post_type='custom'):
    """投稿履歴をログファイルに記録"""
    log_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..',
        'output', 'x_posts', 'post_history.md'
    )

    # ディレクトリがなければ作成
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # ログエントリを作成
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    entry = f"""
### {timestamp}
- タイプ: {post_type}
- 本文: {result.get('text', 'N/A')}
- URL: {result.get('tweet_url', 'N/A')}
- ステータス: {'成功' if result.get('success') else '失敗'}
- 反応: （後で追記）

---
"""

    # ファイルに追記
    if os.path.exists(log_path):
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(entry)
    else:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("# X投稿履歴\n\n")
            f.write(entry)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python post_tweet.py \"ツイート本文\" [--reply-to TWEET_ID] [--quote TWEET_ID]")
        sys.exit(1)

    text = sys.argv[1]
    reply_to = None
    quote_tweet_id = None

    # オプション引数を解析
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--reply-to' and i + 1 < len(sys.argv):
            reply_to = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--quote' and i + 1 < len(sys.argv):
            quote_tweet_id = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    print(f"投稿中: {text[:50]}...")
    result = post_tweet(text, reply_to, quote_tweet_id)

    if result['success']:
        log_post(result)
        print(f"\n投稿成功: {result['tweet_url']}")
