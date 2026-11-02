import { Box } from '@mui/material';
import { useFoodLocation } from '../context/FoodLocationContext';

// Standing notices every customer must see, in both languages.
//
// Both are shown in Bangla *and* English regardless of the language toggle:
// these are not UI chrome, they are disclosures, and a customer who never
// touched the toggle still has to be able to read them. The active language
// leads so the toggle still means something.
export const NOTICES = [
  {
    id: 'variable-prices',
    emoji: '💸',
    en: 'Prices of some items may vary — restaurants can change or update them at any time.',
    bn: 'কিছু খাবারের দাম পরিবর্তনশীল — রেস্তোরাঁ যেকোনো সময় দাম পরিবর্তন বা হালনাগাদ করতে পারে।',
  },
  {
    id: 'under-construction',
    emoji: '🚧',
    en: 'This website is under construction — our mobile app is launching soon!',
    bn: 'ওয়েবসাইটটি নির্মাণাধীন — আমাদের মোবাইল অ্যাপ খুব শীঘ্রই আসছে!',
  },
];

/** Both languages for every notice, active language first. */
export function noticeLines(lang) {
  const order = lang === 'bn' ? ['bn', 'en'] : ['en', 'bn'];
  return NOTICES.flatMap((n) => order.map((l) => `${n.emoji} ${n[l]}`));
}

export default function NoticeMarquee() {
  const { lang } = useFoodLocation() || {};
  const lines = noticeLines(lang);
  const text = lines.join('  •  ');

  return (
    <Box
      role="status"
      aria-label="Site notices"
      sx={{
        position: 'relative', zIndex: 2, overflow: 'hidden', width: '100%',
        bgcolor: 'primary.main', color: 'primary.contrastText',
        fontSize: { xs: 12, sm: 13 }, fontWeight: 700, lineHeight: 1.6, py: 0.6,
        // The track is two identical copies side by side; translating by -50%
        // lands exactly on the start of the second copy, so the loop is seamless
        // with no JS and no measurement.
        '& .notice-track': {
          display: 'flex', width: 'max-content',
          animation: 'noticeScroll 42s linear infinite',
        },
        '& .notice-copy': { pr: 6, whiteSpace: 'nowrap' },
        '@keyframes noticeScroll': {
          from: { transform: 'translateX(0)' },
          to: { transform: 'translateX(-50%)' },
        },
        // Reduced motion gets the notices, not the movement — they wrap onto as
        // many lines as they need instead of scrolling past.
        '@media (prefers-reduced-motion: reduce)': {
          '& .notice-track': { animation: 'none', width: '100%' },
          '& .notice-copy': { whiteSpace: 'normal', pr: 0, textAlign: 'center' },
          '& .notice-copy + .notice-copy': { display: 'none' },
        },
        // Pausing on hover lets someone actually finish reading a long line.
        '&:hover .notice-track': { animationPlayState: 'paused' },
      }}
    >
      <Box className="notice-track">
        {/* aria-hidden on the duplicate: it exists only to close the loop
            visually, and a screen reader must not read the notices twice. */}
        <Box className="notice-copy">{text}</Box>
        <Box className="notice-copy" aria-hidden="true">{text}</Box>
      </Box>
    </Box>
  );
}
