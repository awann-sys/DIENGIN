export async function dispatch(env, request = fetch) {
  const { GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_WORKFLOW, GITHUB_REF } = env;
  if (!GITHUB_TOKEN || !GITHUB_REPOSITORY || !GITHUB_WORKFLOW || !GITHUB_REF) {
    throw new Error('Missing GitHub scheduler configuration or GITHUB_TOKEN secret');
  }
  if (!/^[\w.-]+\/[\w.-]+$/.test(GITHUB_REPOSITORY)) throw new Error('Invalid repository');
  const base = `https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/${encodeURIComponent(GITHUB_WORKFLOW)}`;
  const headers = {
    Authorization: `Bearer ${GITHUB_TOKEN}`,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'DIENGIN-Cloudflare-Scheduler',
  };
  // Avoid adding routine work to an already running/queued production pipeline.
  for (const status of ['in_progress', 'queued', 'waiting', 'pending']) {
    const response = await request(`${base}/runs?branch=${encodeURIComponent(GITHUB_REF)}&status=${status}&per_page=1`, {
      headers, signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new Error(`GitHub run check failed: HTTP ${response.status}`);
    const runs = await response.json();
    if (!Array.isArray(runs.workflow_runs)) throw new Error('Invalid GitHub run response');
    if (runs.workflow_runs.length) return { status: 'skipped', reason: 'pipeline_busy' };
  }
  const response = await request(`${base}/dispatches`, {
    method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ ref: GITHUB_REF }), signal: AbortSignal.timeout(15000),
  });
  if (![200, 204].includes(response.status)) throw new Error(`GitHub dispatch failed: HTTP ${response.status}`);
  return { status: 'dispatched', repository: GITHUB_REPOSITORY, ref: GITHUB_REF };
}

export default {
  async scheduled(controller, env) {
    try {
      console.log(JSON.stringify({ scheduledAt: new Date(controller.scheduledTime).toISOString(), ...await dispatch(env) }));
    } catch (error) {
      console.error(error.message);
      throw error; // Cloudflare invocation must show failure, not a false success.
    }
  },
  fetch(request) {
    const url = new URL(request.url);
    if (request.method !== 'GET' || url.pathname !== '/health') return new Response('Not found', { status: 404 });
    return Response.json({ service: 'diengin-scheduler', status: 'alive', note: 'Liveness only; inspect scheduled invocation logs and GitHub Actions for dispatch success.' });
  },
};

