// Vercel serverless proxy – keeps CORS clean for GitHub Pages dashboard
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Kobo-Token, X-Kobo-Server, X-Asset-Uid');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const token = process.env.KOBO_TOKEN || req.headers['x-kobo-token'];
  if (!token) return res.status(401).json({ error: 'No API token. Set KOBO_TOKEN env var or X-Kobo-Token header.' });

  const server = (req.headers['x-kobo-server'] || 'https://kf.kobotoolbox.org').replace(/\/$/, '');
  const assetUid = req.headers['x-asset-uid'] || req.query.asset_uid;
  if (!assetUid) return res.status(400).json({ error: 'Missing X-Asset-Uid header or asset_uid param.' });

  const action = req.query.action || 'data';
  let url, cacheControl = 'public, s-maxage=300, max-age=60';

  if (action === 'data') {
    const limit = Math.min(parseInt(req.query.limit || '10000', 10), 30000);
    const start = parseInt(req.query.start || '0', 10);
    url = `${server}/api/v2/assets/${assetUid}/data/?format=json&limit=${limit}&start=${start}`;
  } else if (action === 'asset') {
    url = `${server}/api/v2/assets/${assetUid}/?format=json`;
    cacheControl = 'public, s-maxage=3600, max-age=300';
  } else if (action === 'photo') {
    const photoUrl = req.query.url;
    if (!photoUrl) return res.status(400).json({ error: 'Missing url param' });
    if (!photoUrl.includes('kobotoolbox.org') && !photoUrl.includes('kobocat')) {
      return res.status(403).json({ error: 'URL not from KoboToolbox' });
    }
    try {
      const r = await fetch(photoUrl, { headers: { Authorization: `Token ${token}` } });
      if (!r.ok) return res.status(r.status).json({ error: `Photo fetch: ${r.status}` });
      const ct = r.headers.get('content-type') || 'image/jpeg';
      res.setHeader('Content-Type', ct);
      res.setHeader('Cache-Control', 'public, max-age=86400');
      return res.send(Buffer.from(await r.arrayBuffer()));
    } catch (e) {
      return res.status(502).json({ error: e.message });
    }
  } else {
    return res.status(400).json({ error: `Unknown action: ${action}` });
  }

  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 25000);
    const r = await fetch(url, {
      headers: { Authorization: `Token ${token}`, Accept: 'application/json', 'User-Agent': 'DRDIP-II-Dashboard/1.0' },
      signal: ctrl.signal
    });
    clearTimeout(t);
    if (!r.ok) {
      const txt = await r.text();
      return res.status(r.status).json({ error: `Kobo ${r.status}: ${r.statusText}`, detail: txt.slice(0, 300) });
    }
    res.setHeader('Cache-Control', cacheControl);
    return res.status(200).json(await r.json());
  } catch (e) {
    if (e.name === 'AbortError') return res.status(504).json({ error: 'KoboToolbox request timed out (25s)' });
    return res.status(502).json({ error: e.message });
  }
}
