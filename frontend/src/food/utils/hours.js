// Bilingual formatting for opening hours.
//
// The backend sends times as bare "HH:MM" strings and weekdays as 0=Mon..6=Sun
// (Python's datetime.weekday()), deliberately without any prose — the customer
// may be reading the site in Bangla or English, and only the client knows
// which. Everything user-visible about hours is formatted here so the menu, the
// cards and the toast can never drift apart.

const BN_DIGITS = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];

/** Western digits → Bangla digits. "10:30" → "১০:৩০" */
export const bnDigits = (s) => String(s).replace(/[0-9]/g, (d) => BN_DIGITS[Number(d)]);

const DAYS = {
  en: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
  bn: ['সোমবার', 'মঙ্গলবার', 'বুধবার', 'বৃহস্পতিবার', 'শুক্রবার', 'শনিবার', 'রবিবার'],
};

export const dayName = (weekday, lang) => (DAYS[lang === 'bn' ? 'bn' : 'en'][weekday] ?? '');

// Bangla names the part of the day rather than using AM/PM, so "10:30 AM"
// reads as "সকাল ১০:৩০".
const bnPartOfDay = (hour) => {
  if (hour >= 4 && hour < 12) return 'সকাল';
  if (hour >= 12 && hour < 16) return 'দুপুর';
  if (hour >= 16 && hour < 19) return 'বিকাল';
  return 'রাত';
};

/** "14:30" → "2:30 PM" (en) / "দুপুর ২:৩০" (bn). Returns '' for junk input. */
export function formatTime(hhmm, lang) {
  const m = /^(\d{1,2}):(\d{2})/.exec(String(hhmm || ''));
  if (!m) return '';
  const hour = Number(m[1]);
  const minute = m[2];
  if (lang === 'bn') return `${bnPartOfDay(hour)} ${bnDigits(`${hour % 12 || 12}:${minute}`)}`;
  return `${hour % 12 || 12}:${minute} ${hour < 12 ? 'AM' : 'PM'}`;
}

/**
 * "Opens tomorrow at 10:30 AM" from the serializer's `next_open`
 * ({weekday, open_time, days_ahead}). Null input means the restaurant has made
 * no promise — the master switch is off or no hours exist — and callers should
 * say so plainly rather than invent a time.
 */
export function nextOpenText(nextOpen, lang) {
  const bn = lang === 'bn';
  if (!nextOpen) return bn ? 'এখন বন্ধ' : 'Closed right now';
  const at = formatTime(nextOpen.open_time, lang);
  if (nextOpen.days_ahead === 0) return bn ? `আজ ${at}-এ খুলবে` : `Opens today at ${at}`;
  if (nextOpen.days_ahead === 1) return bn ? `আগামীকাল ${at}-এ খুলবে` : `Opens tomorrow at ${at}`;
  const day = dayName(nextOpen.weekday, lang);
  return bn ? `${day} ${at}-এ খুলবে` : `Opens ${day} at ${at}`;
}

/** The full sentence shown when someone taps a dish at a closed restaurant. */
export function closedToastText(restaurantName, nextOpen, lang) {
  const when = nextOpenText(nextOpen, lang);
  return lang === 'bn'
    ? `${restaurantName} এখন বন্ধ — ${when}।`
    : `${restaurantName} is closed right now — ${when.replace(/^Opens/, 'opens')}.`;
}
