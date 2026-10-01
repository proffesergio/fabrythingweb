import axios from 'axios';
import config from '../utils/config';

const BASE = 'store/nobleseek/';

function unwrap(res) { return res?.data?.data ?? res?.data; }

export async function fetchNewsList({ category = '', search = '', page = 1, featured = '' } = {}) {
  const res = await axios.get(`${config.API_URL}${BASE}articles/`, { params: { category, search, page, featured } });
  const raw = unwrap(res);
  // DRF paginated {results,count} or plain list — normalize both.
  if (raw && Array.isArray(raw.results)) return { results: raw.results, count: raw.count, next: raw.next };
  if (Array.isArray(raw)) return { results: raw, count: raw.length, next: null };
  return { results: [], count: 0, next: null };
}

export async function fetchNewsDetail(slug) {
  const res = await axios.get(`${config.API_URL}${BASE}articles/${slug}/`);
  return unwrap(res);
}

export async function fetchRelated(slug) {
  const res = await axios.get(`${config.API_URL}${BASE}articles/${slug}/related/`);
  return unwrap(res) || [];
}

export async function fetchNewsCategories() {
  const res = await axios.get(`${config.API_URL}${BASE}categories/`);
  return unwrap(res) || [];
}

export async function fetchLatestStrip() {
  try {
    const res = await axios.get(`${config.API_URL}${BASE}latest/`);
    return unwrap(res) || [];
  } catch { return []; }
}

export function timeAgo(iso) {
  if (!iso) return '';
  const s = Math.max(1, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function articleUrl(slug, utm = 'nobleseek-fb') {
  return `/nobleseek/${slug}?utm_source=facebook&utm_medium=social&utm_campaign=${encodeURIComponent(utm)}`;
}
