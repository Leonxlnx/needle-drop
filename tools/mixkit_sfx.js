// Usage: node tools/mixkit_sfx.js <mixkit sfx listing url|search term> ... -> id | title | duration | wav url
const args = process.argv.slice(2);
(async () => {
  for (const a of args) {
    const u = a.startsWith('http') ? a : `https://mixkit.co/free-sound-effects/discover/${encodeURIComponent(a)}/`;
    const html = await (await fetch(u, { headers: { 'User-Agent': 'Mozilla/5.0' } })).text();
    const re = /data-audio-player-item-id-value="(\d+)"[\s\S]*?item-grid-card__title">\s*([^<]+?)\s*<\/h2>[\s\S]*?data-test-id="duration">\s*([0-9:]+)/g;
    let m, n = 0;
    console.log(`# ${u}`);
    while ((m = re.exec(html))) { n++; console.log(`${m[1]} | ${m[2]} | ${m[3]} | https://assets.mixkit.co/active_storage/sfx/${m[1]}/${m[1]}.wav`); }
    if (!n) console.log('  (none)');
  }
})();
