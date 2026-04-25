/**
 * Slack Events を受信して GitHub Actions をトリガーする Cloudflare Worker
 *
 * 環境変数（Cloudflare Workers の Settings で設定）:
 * - GITHUB_PAT: GitHub Personal Access Token (repo scope)
 * - GITHUB_REPO: リポジトリ名 (例: kocchan/note-uploader)
 * - SLACK_SIGNING_SECRET: Slack App の Signing Secret
 */

export default {
  async fetch(request, env) {
    // POST リクエストのみ処理
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    const url = new URL(request.url);

    // /slack/events エンドポイント
    if (url.pathname === '/slack/events') {
      return handleSlackEvent(request, env);
    }

    return new Response('Not found', { status: 404 });
  }
};

/**
 * Slack Event を処理
 */
async function handleSlackEvent(request, env) {
  const body = await request.text();
  const payload = JSON.parse(body);

  // Slack URL verification (初回設定時)
  if (payload.type === 'url_verification') {
    return new Response(payload.challenge, {
      headers: { 'Content-Type': 'text/plain' }
    });
  }

  // Slack Signing Secret で検証（セキュリティ）
  const isValid = await verifySlackRequest(request, body, env.SLACK_SIGNING_SECRET);
  if (!isValid) {
    return new Response('Invalid signature', { status: 401 });
  }

  // Event callback の処理
  if (payload.type === 'event_callback') {
    const event = payload.event;

    // Bot 自身のイベントは無視
    if (event.bot_id) {
      return new Response('OK');
    }

    // イベントタイプに応じて GitHub Actions をトリガー
    let eventType = null;
    let clientPayload = {};

    switch (event.type) {
      case 'app_mention':
        // @note-bot へのメンション
        eventType = 'slack-command';
        clientPayload = {
          channel: event.channel,
          user: event.user,
          text: event.text,
          ts: event.ts,
          thread_ts: event.thread_ts || event.ts
        };
        break;

      case 'reaction_added':
        // リアクション追加（✅ ❌ ✏️ など）
        eventType = 'slack-reaction';
        clientPayload = {
          channel: event.item.channel,
          message_ts: event.item.ts,
          reaction: event.reaction,
          user: event.user
        };
        break;

      case 'message':
        // チャンネルメッセージ（必要に応じて）
        // 現時点では app_mention のみ処理
        break;

      default:
        // その他のイベントは無視
        break;
    }

    // GitHub Actions をトリガー
    if (eventType) {
      await triggerGitHubAction(env, eventType, clientPayload);
    }
  }

  // Slack は 3秒以内にレスポンスが必要
  return new Response('OK');
}

/**
 * Slack リクエストの署名を検証
 */
async function verifySlackRequest(request, body, signingSecret) {
  const timestamp = request.headers.get('X-Slack-Request-Timestamp');
  const signature = request.headers.get('X-Slack-Signature');

  if (!timestamp || !signature) {
    return false;
  }

  // 5分以上前のリクエストは拒否（リプレイ攻撃対策）
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - parseInt(timestamp)) > 300) {
    return false;
  }

  // 署名を計算
  const sigBasestring = `v0:${timestamp}:${body}`;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(signingSecret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signatureBytes = await crypto.subtle.sign(
    'HMAC',
    key,
    encoder.encode(sigBasestring)
  );
  const computedSignature = 'v0=' + Array.from(new Uint8Array(signatureBytes))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  return computedSignature === signature;
}

/**
 * GitHub Actions の repository_dispatch をトリガー
 */
async function triggerGitHubAction(env, eventType, clientPayload) {
  const [owner, repo] = env.GITHUB_REPO.split('/');
  const url = `https://api.github.com/repos/${owner}/${repo}/dispatches`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.GITHUB_PAT}`,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'note-business-slack-worker',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      event_type: eventType,
      client_payload: clientPayload
    })
  });

  if (!response.ok) {
    console.error(`GitHub API error: ${response.status} ${await response.text()}`);
  }

  return response.ok;
}
