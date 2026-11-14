const fs = require('node:fs');
const path = require('node:path');

function packageStoreShell(buildDirectory, moduleDirectory) {
  const index = path.join(buildDirectory, 'index.html');
  const shell = fs.readFileSync(index, 'utf8');
  if (!shell.includes('/static/js/')) throw new Error('Built application assets are missing');
  fs.mkdirSync(moduleDirectory, {recursive: true});
  // A literal require is traced into the function, independently of runtime cwd.
  fs.writeFileSync(path.join(moduleDirectory, 'build-shell.cjs'), 'module.exports = ' + JSON.stringify(shell) + ';\n');
  fs.writeFileSync(path.join(buildDirectory, 'app-shell.html'), shell);
  // Vercel serves filesystem index.html before rewrites. Keep the SPA fallback
  // under a different name so / reaches the crawlable document function.
  fs.unlinkSync(index);
}

if (require.main === module) {
  packageStoreShell(path.resolve(__dirname, '../build'), path.resolve(__dirname, '../server'));
}
module.exports = {packageStoreShell};
