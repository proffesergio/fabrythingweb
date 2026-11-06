// API base URL. Falls back to the local backend so a missing/late .env
// (a classic CRA trap: env is baked in at `npm start` time) can't silently
// point every request at the dev server and blank out the storefront.
const config={
    API_URL:typeof window !== 'undefined' && window.location.hostname === 'nobleseek.fabrything.com'
        ? '/api/'
        : process.env.REACT_APP_API_URL || "http://localhost:8000/api/"
}
export default config;
