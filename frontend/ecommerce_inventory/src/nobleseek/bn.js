// Bangla date / number helpers for the NobleSeek news portal.

const BN_DIGITS = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];

export const toBn = (v) => String(v ?? '').replace(/[0-9]/g, (d) => BN_DIGITS[+d]);

export const WEEKDAYS = ['রবিবার', 'সোমবার', 'মঙ্গলবার', 'বুধবার', 'বৃহস্পতিবার', 'শুক্রবার', 'শনিবার'];

export const MONTHS = ['জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন', 'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর'];

function dayPeriod(h) {
  if (h < 4) return 'রাত';
  if (h < 6) return 'ভোর';
  if (h < 11) return 'সকাল';
  if (h < 15) return 'দুপুর';
  if (h < 18) return 'বিকেল';
  if (h < 20) return 'সন্ধ্যা';
  return 'রাত';
}

/** "বৃহস্পতিবার, ১ অক্টোবর ২০২৬" — portal top bar. */
export function todayLine(d = new Date()) {
  return `${WEEKDAYS[d.getDay()]}, ${toBn(d.getDate())} ${MONTHS[d.getMonth()]} ${toBn(d.getFullYear())}`;
}

/** "১ অক্টোবর ২০২৬, বিকেল ৪:৩৫" — article bylines. */
export function formatNewsTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const mins = String(d.getMinutes()).padStart(2, '0');
  return `${toBn(d.getDate())} ${MONTHS[d.getMonth()]} ${toBn(d.getFullYear())}, ${dayPeriod(d.getHours())} ${toBn(d.getHours())}:${toBn(mins)}`;
}

/** Compact view counts: ৮৫০ → "৮৫০", ১২,৪০০ → "১২.৪ হাজার", ৩,২০,০০০ → "৩.২ লাখ". */
export function formatViews(n) {
  const v = Number(n) || 0;
  if (v >= 100000) {
    const lakh = (v / 100000).toFixed(1).replace(/\.0$/, '');
    return `${toBn(lakh)} লাখ`;
  }
  if (v >= 1000) {
    const k = (v / 1000).toFixed(1).replace(/\.0$/, '');
    return `${toBn(k)} হাজার`;
  }
  return toBn(v);
}

/** "৫ মিনিট আগে" — card timestamps, portal style. */
export function timeAgoBn(iso) {
  if (!iso) return '';
  const s = Math.max(1, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return `${toBn(s)} সেকেন্ড আগে`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${toBn(m)} মিনিট আগে`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${toBn(h)} ঘণ্টা আগে`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${toBn(d)} দিন আগে`;
  const dt = new Date(iso);
  return `${toBn(dt.getDate())} ${MONTHS[dt.getMonth()]} ${toBn(dt.getFullYear())}`;
}
