import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker from './worker.mjs';

async function simulate(outcomes, env = {}) {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push(String(url));
    assert.ok(options.signal);
    assert.ok(String(url).includes(':generateContent'), 'POST must not list models');
    const outcome = outcomes[calls.length - 1];
    if (outcome === 'timeout') throw new DOMException('Timed out', 'AbortError');
    if (outcome === 'html') return new Response('unavailable', { status: 503 });
    if (outcome === 'blocked') return Response.json({ promptFeedback: { blockReason: 'SAFETY' } });
    if (outcome === 'bad-json') return Response.json({ candidates: [{ content: { parts: [{ text: 'incomplete' }] } }] });
    if (outcome === 200) return Response.json({ candidates: [{ finishReason: 'STOP', content: { parts: [{ text: '{"valid":false}' }] } }] });
    return Response.json({ error: { message: 'Upstream failure' } }, { status: outcome });
  };
  try {
    const result = await worker.fetch(new Request('https://example.com', {
      method: 'POST', body: JSON.stringify({ prompt: 'Test topic' }),
    }), { API_KEY: 'test', MODELS: 'first,second', ...env });
    return { status: result.status, data: await result.json(), calls };
  } finally { globalThis.fetch = original; }
}

for (const failure of [429, 503, 404, 'timeout', 'html', 'bad-json']) {
  test(`falls back after ${failure}`, async () => {
    const result = await simulate([failure, 200]);
    assert.equal(result.status, 200);
    assert.equal(result.calls.length, 2);
    assert.equal(result.data.model, 'second');
    assert.equal(result.data.reply, '{"valid":false}');
  });
}

test('all limited models stop with quota explanation', async () => {
  const result = await simulate([429, 429]);
  assert.equal(result.status, 429);
  assert.equal(result.data.attempts.length, 2);
});

test('all timed out models produce timeout code', async () => {
  const result = await simulate(['timeout', 'timeout']);
  assert.equal(result.status, 504);
  assert.equal(result.data.code, 'timeout');
});

test('auth failures and blocked content do not trigger fallback', async () => {
  for (const [failure, status] of [[403, 403], ['blocked', 422]]) {
    const result = await simulate([failure]);
    assert.equal(result.status, status);
    assert.equal(result.calls.length, 1);
  }
});

test('success uses only one generation call', async () => {
  const result = await simulate([200]);
  assert.equal(result.status, 200);
  assert.equal(result.calls.length, 1);
});
