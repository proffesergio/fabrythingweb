// Isolated verification output; never replaces a running server's build folder.
const path = require('path');
const os = require('os');
try { os.setPriority(0, 10); } catch (_) { /* Optional process priority. */ }
process.env.NODE_ENV = 'production';
process.env.BABEL_ENV = 'production';
process.env.CI = 'false';
process.env.GENERATE_SOURCEMAP = 'false';
process.env.BUILD_PATH = process.env.BUILD_PATH || path.resolve(__dirname, '../../.local-validation/build');
const configPath = require.resolve('react-scripts/config/webpack.config');
const factory = require(configPath);
require.cache[configPath].exports = (...args) => {
  const config = factory(...args);
  for (const plugin of config.optimization.minimizer || []) {
    if (plugin.options && Object.prototype.hasOwnProperty.call(plugin.options, 'parallel')) plugin.options.parallel = false;
  }
  return config;
};
require('react-scripts/scripts/build');
