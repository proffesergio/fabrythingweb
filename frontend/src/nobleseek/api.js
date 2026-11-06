import axios from 'axios';
import config from '../utils/config';

const BASE = 'store/nobleseek/';

function unwrap(res) { return res?.data?.data ?? res?.data; }

export async function fetchNewsList({ category = '', search = '', page = 1, featured = '', breaking = '', popular = '' } = {}) {
  const res = await axios.get(`${config.API_URL}${BASE}articles/`, { params: { category, search, page, featured, breaking, popular } });
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
  const categories = unwrap(res);
  return Array.isArray(categories) ? [...categories].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0) || (a.id ?? 0) - (b.id ?? 0)) : [];
}

export async function fetchLatestStrip() {
  try {
    const res = await axios.get(`${config.API_URL}${BASE}latest/`);
    return unwrap(res) || [];
  } catch { return []; }
}

// Portal homepage data: most-read sidebar, breaking ticker, sections.
export async function fetchPopular(limit = 5) {
  try {
    const res = await axios.get(`${config.API_URL}${BASE}articles/`, { params: { popular: '1' } });
    const raw = unwrap(res);
    const list = (raw && raw.results) || raw || [];
    return list.slice(0, limit);
  } catch { return []; }
}

export async function fetchSection(category, limit = 5) {
  try {
    const { results } = await fetchNewsList({ category });
    return (results || []).slice(0, limit);
  } catch { return []; }
}

export async function fetchBreaking(limit = 6) {
  try {
    const { results } = await fetchNewsList({ breaking: '1' });
    return (results || []).slice(0, limit);
  } catch { return []; }
}

// Fallback section labels when the categories API is unreachable.
export const PORTAL_SECTIONS = [
  { slug: 'bangladesh', name: 'বাংলাদেশ' },
  { slug: 'politics', name: 'রাজনীতি' },
  { slug: 'world', name: 'আন্তর্জাতিক' },
  { slug: 'economy', name: 'অর্থনীতি' },
  { slug: 'business', name: 'বাণিজ্য' },
  { slug: 'sports', name: 'খেলা' },
  { slug: 'entertainment', name: 'বিনোদন' },
  { slug: 'lifestyle', name: 'জীবনযাপন' },
  { slug: 'tech', name: 'প্রযুক্তি ও স্টার্টআপ' },
  { slug: 'opinion', name: 'মতামত' },
  { slug: 'analysis', name: 'বিশ্লেষণ' },
  { slug: 'explainer', name: 'এক্সপ্লেইনার' },
  { slug: 'feature', name: 'ফিচার' },
  { slug: 'culture', name: 'সংস্কৃতি' },
  { slug: 'easel', name: 'ইজেল' },
  { slug: 'offbeat', name: 'অফবিট' },
  { slug: 'country', name: 'সারাদেশ' },
  { slug: 'corporate', name: 'কর্পোরেট' },
  { slug: 'jobs', name: 'চাকরি' },
  { slug: 'expatriate', name: 'প্রবাস' },
  { slug: 'education', name: 'শিক্ষা' },
  { slug: 'health', name: 'স্বাস্থ্য' },
  { slug: 'environment', name: 'পরিবেশ' },
  { slug: 'crime', name: 'অপরাধ' },
  { slug: 'court', name: 'আদালত' },
  { slug: 'video', name: 'ভিডিও' },
  { slug: 'multimedia', name: 'মাল্টিমিডিয়া' },
  { slug: 'ai', name: 'কৃত্রিম বুদ্ধিমত্তা' },
];

export function sectionName(slug, cats = []) {
  const hit = (cats || []).find((c) => c.slug === slug);
  if (hit) return hit.name;
  return (PORTAL_SECTIONS.find((c) => c.slug === slug) || {}).name || 'সংবাদ';
}

export async function fetchInfoPage(slug) {
  const res = await axios.get(`${config.API_URL}${BASE}pages/${slug}/`);
  return unwrap(res);
}

export async function fetchComments(articleId) {
  const res = await axios.get(`${config.API_URL}${BASE}comments/`, { params: { article: articleId } });
  return unwrap(res) || [];
}

export async function postComment(articleId, name, text) {
  const res = await axios.post(`${config.API_URL}${BASE}comments/`, { article: articleId, name, text });
  return unwrap(res);
}

export async function flagComment(id) {
  const res = await axios.post(`${config.API_URL}${BASE}comments/${id}/flag/`, {});
  return unwrap(res);
}

export async function fetchPolls() {
  try {
    const res = await axios.get(`${config.API_URL}${BASE}polls/`);
    return unwrap(res) || [];
  } catch { return []; }
}

export async function votePoll(pollId, optionId, sessionKey) {
  const res = await axios.post(`${config.API_URL}${BASE}polls/${pollId}/vote/`,
    { option_id: optionId, session_key: sessionKey });
  return unwrap(res);
}

export function getPollSession() {
  try {
    let s = localStorage.getItem('ns_poll_session');
    if (!s) {
      s = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem('ns_poll_session', s);
    }
    return s;
  } catch { return `anon-${Date.now().toString(36)}`; }
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
  const origin = process.env.NODE_ENV === 'production' ? 'https://nobleseek.fabrything.com' : '';
  return `${origin}/nobleseek/${encodeURIComponent(slug)}?utm_source=facebook&utm_medium=social&utm_campaign=${encodeURIComponent(utm)}`;
}
