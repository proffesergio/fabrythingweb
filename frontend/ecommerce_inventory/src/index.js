import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import {Provider} from 'react-redux';
import store from './redux/store/store'
import axios from 'axios';
import config from './utils/config';
import { getToken } from './utils/authToken';
import { applyUpdate, registerServiceWorker } from './utils/pwa';

// Set default Authorization header. getToken() refuses to hand back an expired
// token (and drops it), so a months-old session can't poison every request the
// app makes — see utils/authToken.js.
const bootToken = getToken();
axios.defaults.headers.common['Authorization'] = bootToken ? `Bearer ${bootToken}` : '';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <Provider store={store}>
    <App />
  </Provider>
);

// The service worker exists to make the site installable (Chrome refuses the
// install prompt without one) and to speed up repeat launches. It never caches
// HTML or /api/ responses — see public/sw.js for the reasoning.
//
// A new deploy is picked up on the next navigation regardless; this prompt only
// offers to refresh an already-open tab so a customer mid-checkout is never
// reloaded out from under themselves.
registerServiceWorker({
  onUpdateReady: (registration) => {
    const bar = document.createElement('div');
    bar.setAttribute('role', 'status');
    bar.style.cssText = [
      'position:fixed', 'left:12px', 'right:12px', 'bottom:12px', 'z-index:2147483647',
      'background:#0F172A', 'color:#fff', 'padding:12px 14px', 'border-radius:12px',
      'font:600 14px system-ui,-apple-system,Segoe UI,Roboto,sans-serif',
      'box-shadow:0 10px 30px rgba(0,0,0,.35)', 'display:flex', 'align-items:center', 'gap:12px',
    ].join(';');
    bar.innerHTML =
      '<span style="flex:1">A new version of Fabrything is ready.</span>' +
      '<button type="button" style="background:#E85D4A;color:#fff;border:0;border-radius:8px;' +
      'padding:8px 14px;font:inherit;cursor:pointer">Refresh</button>' +
      '<button type="button" aria-label="Dismiss" style="background:transparent;color:#94A3B8;' +
      'border:0;font:inherit;cursor:pointer;padding:8px">\u2715</button>';
    const [refresh, dismiss] = bar.querySelectorAll('button');
    refresh.addEventListener('click', () => applyUpdate(registration));
    dismiss.addEventListener('click', () => bar.remove());
    document.body.appendChild(bar);
  },
});

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
