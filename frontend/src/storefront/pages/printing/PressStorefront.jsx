import React, { useRef, useState } from 'react';
import { Box, Typography } from '@mui/material';
import PressShowcase from './PressShowcase';
import PressOrderWizard from './PressOrderWizard';

// Press tab composition: ColorLifePrint-style catalog on top, live
// calculator + artwork + checkout below. "Order this design" scrolls to the
// wizard with the linked press product preselected.
export default function PressStorefront() {
  const [wizardProductId, setWizardProductId] = useState(null);
  const wizardRef = useRef(null);

  const handleOrder = (pressProductId) => {
    if (pressProductId) setWizardProductId(pressProductId);
    requestAnimationFrame(() => {
      wizardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  return (
    <Box>
      <Typography variant="h6" fontWeight={800} sx={{ mb: 0.5 }}>Web-to-Press Printing</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Business cards, flyers, banners and more — instant pricing, print-ready upload
        with bleed guides, and bKash / Nagad / Rocket / SSLCommerz checkout with
        inside- and outside-Dhaka courier delivery.
      </Typography>
      <PressShowcase onOrder={handleOrder} />
      <Box ref={wizardRef} sx={{ scrollMarginTop: 16 }}>
        <PressOrderWizard initialProductId={wizardProductId} />
      </Box>
    </Box>
  );
}
