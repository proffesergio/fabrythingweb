import { Box } from '@mui/material';
import { keyframes } from '@emotion/react';
import { useFoodTheme } from '../context/FoodThemeContext';
import { foodTokens } from '../theme';

// A calm "food cosmos": warm nebula blobs + drifting food planets/stars behind the
// content. Everything is low-opacity and slow so text/cards stay perfectly readable.
const drift = keyframes`
  0%   { transform: translate(0,0) rotate(0deg); }
  50%  { transform: translate(22px,-26px) rotate(14deg); }
  100% { transform: translate(0,0) rotate(0deg); }
`;
const twinkle = keyframes`
  0%,100% { opacity: .05; }
  50%     { opacity: .16; }
`;
const orbit = keyframes`
  from { transform: rotate(0deg) translateX(38px) rotate(0deg); }
  to   { transform: rotate(360deg) translateX(38px) rotate(-360deg); }
`;

// Deterministic layout (no re-random on render).
const PLANETS = [
  ['🍛', 8, 12, 46, 26], ['🍔', 22, 78, 40, 30], ['🍕', 62, 8, 52, 34], ['🍜', 78, 70, 44, 28],
  ['🍚', 40, 45, 34, 24], ['🍗', 15, 55, 38, 32], ['🥘', 70, 40, 42, 36], ['🧁', 88, 22, 30, 22],
  ['🍩', 33, 90, 34, 27], ['🥟', 55, 62, 30, 25], ['🍤', 90, 55, 34, 31], ['🫓', 48, 20, 28, 23],
];
const STARS = [
  [18, 30], [30, 68], [46, 14], [58, 82], [72, 24], [84, 60], [12, 84], [66, 52], [38, 40], [92, 38],
];

export default function FoodGalaxy() {
  // This sheet is `position: fixed; inset: 0` behind every food page, so its base
  // colour IS the page background. Hardcoding the light canvas here left dark-mode
  // text (a warm off-white) sitting on a near-white sheet — headings rendered
  // directly on the canvas, like the menu category titles, became invisible while
  // text inside Cards stayed readable because Cards paint their own surface.
  const { mode } = useFoodTheme();
  const isDark = mode === 'dark';
  const C = foodTokens(mode);
  // Nebulae need more punch on a dark canvas to read at all, less on a light one.
  const a = (light, dark) => (isDark ? dark : light);

  return (
    <Box aria-hidden sx={{
      position: 'fixed', inset: 0, zIndex: 0, overflow: 'hidden', pointerEvents: 'none',
      // warm base + soft spice nebulae
      background: `
        radial-gradient(60% 55% at 15% 12%, rgba(244,166,42,${a(0.16, 0.10)}), transparent 60%),
        radial-gradient(55% 50% at 85% 20%, rgba(232,69,43,${a(0.14, 0.12)}), transparent 62%),
        radial-gradient(60% 60% at 70% 90%, rgba(47,125,79,${a(0.10, 0.09)}), transparent 60%),
        ${C.canvas}`,
      '@media (prefers-reduced-motion: reduce)': { '& *': { animation: 'none !important' } },
    }}>
      {/* slow-orbiting nebula glow */}
      <Box sx={{ position: 'absolute', top: '30%', left: '50%', width: 520, height: 520, borderRadius: '50%',
        background: `radial-gradient(circle, rgba(232,69,43,${a(0.10, 0.14)}), transparent 70%)`, filter: 'blur(30px)',
        animation: `${drift} 40s ease-in-out infinite` }} />

      {STARS.map(([t, l], i) => (
        <Box key={`s${i}`} sx={{ position: 'absolute', top: `${t}%`, left: `${l}%`, width: 5, height: 5,
          borderRadius: '50%', bgcolor: C.primary, animation: `${twinkle} ${5 + (i % 4)}s ease-in-out ${i * 0.4}s infinite` }} />
      ))}

      {PLANETS.map(([e, t, l, size, dur], i) => (
        <Box key={`p${i}`} component="span" sx={{ position: 'absolute', top: `${t}%`, left: `${l}%`,
          fontSize: size, opacity: a(0.1, 0.14), willChange: 'transform',
          animation: `${drift} ${dur}s ease-in-out ${i * 0.6}s infinite` }}>
          <Box component="span" sx={{ display: 'inline-block', animation: `${orbit} ${dur * 1.6}s linear infinite` }}>{e}</Box>
        </Box>
      ))}
    </Box>
  );
}
