// Usage: node tools/mixkit_list.js <mixkit listing url> ... -> prints name | duration | mp3 | page
const urls = process.argv.slice(2);
(async () => {
  for (const u of urls) {
    const html = await (await fetch(u, { headers: { 'User-Agent': 'Mozilla/5.0' } })).text();
    const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(m => { try { return JSON.parse(m[1]) } catch { return null } }).filter(Boolean);
    const items = [];
    const walk = o => { if (!o || typeof o !== 'object') return; if (Array.isArray(o)) return o.forEach(walk);
      if ((o['@type'] === 'MusicRecording' || o['@type'] === 'AudioObject') && (o.name)) items.push(o);
      Object.values(o).forEach(walk) };
    blocks.forEach(walk);
    const seen = new Set();
    for (const it of items) {
      const mp3 = it.audio?.contentUrl || it.contentUrl || '';
      const key = it.name + mp3; if (seen.has(key)) continue; seen.add(key);
      console.log([it.name, it.duration || it.audio?.duration || '', mp3, it.url || it['@id'] || '', (it.byArtist?.name || '')].join(' | '));
    }
    if (!items.length) console.log('NO_ITEMS', u, [...new Set(html.match(/https:\/\/assets\.mixkit\.co\/[^"]+\.mp3/g) || [])].length, 'raw mp3 urls');
  }
})();
