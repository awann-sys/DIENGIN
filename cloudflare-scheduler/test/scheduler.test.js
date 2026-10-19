import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker, { dispatch } from '../src/index.js';

const env = { GITHUB_TOKEN: 'test-secret', GITHUB_REPOSITORY: 'awann-sys/DIENGIN', GITHUB_WORKFLOW: 'diengin-cloud.yml', GITHUB_REF: 'main' };
test('dispatch targets the production workflow and main branch', async () => {
  const calls = [];
  const result = await dispatch(env, async (url, options) => {
    calls.push({ url, options });
    return options.method === 'POST' ? new Response(null, { status: 204 }) : Response.json({ workflow_runs: [] });
  });
  assert.equal(result.status, 'dispatched');
  assert.equal(calls.length, 5);
  assert.ok(calls[4].url.endsWith('/diengin-cloud.yml/dispatches'));
  assert.deepEqual(JSON.parse(calls[4].options.body), { ref: 'main' });
});
test('busy pipeline is skipped without dispatch', async () => {
  let count = 0;
  assert.equal((await dispatch(env, async () => { count++; return Response.json({ workflow_runs: [{ id: 1 }] }); })).status, 'skipped');
  assert.equal(count, 1);
});
test('dispatch also accepts the newer success response', async () => {
  assert.equal((await dispatch(env, async (_, options) => Response.json(options.method === 'POST' ? { workflow_run_id: 1 } : { workflow_runs: [] }))).status, 'dispatched');
});
test('authentication failure stops before dispatch', async () => {
  await assert.rejects(dispatch(env, async () => new Response(null, { status: 401 })), /HTTP 401/);
});
test('dispatch rejection is reported as failure', async () => {
  await assert.rejects(dispatch(env, async (_, options) => options.method === 'POST' ? new Response(null, { status: 403 }) : Response.json({ workflow_runs: [] })), /HTTP 403/);
});
test('missing secret never sends a request', async () => {
  await assert.rejects(dispatch({ ...env, GITHUB_TOKEN: '' }, () => assert.fail('Unexpected request')), /Missing/);
});
test('public endpoints cannot trigger a pipeline', async () => {
  assert.equal(worker.fetch(new Request('https://example.com/trigger', { method: 'POST' })).status, 404);
  assert.equal(worker.fetch(new Request('https://example.com/health')).status, 200);
});

