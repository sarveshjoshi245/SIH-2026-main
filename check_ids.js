const fs = require('fs');
const html = fs.readFileSync('server/public/dashboard.html', 'utf8');

// Extract JS from script tags
const scriptMatches = html.match(/<script[\s\S]*?<\/script>/gi) || [];
const js = scriptMatches.join('\n');

// Extract all getElementById references from JS
const re = /getElementById\s*\(\s*[`'"]([\w-]+)[`'"]\s*\)/g;
const jsIds = new Set();
let m;
while ((m = re.exec(js)) !== null) jsIds.add(m[1]);

// Remove script tags from HTML to get just the markup
const htmlOnly = html.replace(/<script[\s\S]*?<\/script>/gi, '');

// Check which IDs from JS are missing in HTML markup
const missing = [];
const present = [];
for (const id of Array.from(jsIds).sort()) {
  const pattern = `id="${id}"`;
  if (htmlOnly.includes(pattern)) {
    present.push(id);
  } else {
    missing.push(id);
  }
}

console.log(`\nTOTAL IDs referenced in JS: ${jsIds.size}`);
console.log(`Present in HTML: ${present.length}`);
console.log(`MISSING from HTML: ${missing.length}`);
if (missing.length > 0) {
  console.log('\nMISSING HTML ELEMENTS (JS references these but no matching id= in HTML):');
  missing.forEach(id => console.log(`  - ${id}`));
}
