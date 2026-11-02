# Fabrything frontend

React 18 with Create React App, Material UI, Redux Toolkit, Framer Motion and
Swiper. The app runs directly from this directory.

See [local setup](../docs/SETUP.md) for the API environment and admin account.

```bash
npm ci
npm start
npm test -- --watchAll=false --runInBand
npm run build
```

Customer shop code lives in src/storefront/. Admin, vendor, rider, food and
NobleSeek interfaces have their own directories under src/. Shared components,
Redux state, hooks and utilities live alongside them.
Browser scripts in scripts/ write evidence to ../docs/screenshots/.

Vercel project fabrythingweb uses this directory as its root. Its vercel.json
handles API proxying, sitemap routing and SPA fallback. Generated build/ output
and node_modules/ are excluded from source control.
