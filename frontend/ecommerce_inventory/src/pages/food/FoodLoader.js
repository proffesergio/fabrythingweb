import { Box, Typography } from "@mui/material";
import { keyframes } from "@emotion/react";

// Food-themed indeterminate loader: a dish slides + bounces along a warm progress track.
const slide = keyframes`
  0%   { left: -18%; }
  100% { left: 100%; }
`;
const bounce = keyframes`
  0%, 100% { transform: translateY(0) rotate(-4deg); }
  50%      { transform: translateY(-9px) rotate(6deg); }
`;

export default function FoodLoader({ label = "Loading…", emoji = "🍲" }) {
  return (
    <Box sx={{ py: 4, textAlign: "center", maxWidth: 360, mx: "auto",
      "@media (prefers-reduced-motion: reduce)": { "& *": { animation: "none !important" } } }}>
      <Box sx={{ position: "relative", height: 32, mb: 1 }}>
        <Box component="span" sx={{ position: "absolute", fontSize: 26, top: 0,
          animation: `${slide} 1.5s ease-in-out infinite, ${bounce} .75s ease-in-out infinite` }}>
          {emoji}
        </Box>
      </Box>
      <Box sx={{ position: "relative", height: 6, borderRadius: 3, bgcolor: "#F0E6DB", overflow: "hidden" }}>
        <Box sx={{ position: "absolute", top: 0, bottom: 0, width: "35%", borderRadius: 3,
          background: "linear-gradient(90deg,#F4A62A,#E8452B)", animation: `${slide} 1.5s ease-in-out infinite` }} />
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ mt: 1.2, display: "block", fontWeight: 600 }}>
        {label}
      </Typography>
    </Box>
  );
}
