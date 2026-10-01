import React from 'react';
import { Container, Typography, Box } from '@mui/material';
import NewsSeo from '../components/NewsSeo';

const DOCS = {
  about: {
    title: 'About NobleSeek',
    body: `<p><strong>NobleSeek by Fabrything</strong> is a trends-driven Bangla news desk. Topics come from Google Trends (Bangladesh + worldwide), updated daily. Every story is human-written (600-1000 words), with 1 verified hero image, source credit, and tags.</p><p>We exist to turn viral curiosity into verified reading — and to fund it with clearly-labelled advertising, so the shop can stay low-ad and fast.</p><p>Contact: support@fabrything.com, Dhaka, Bangladesh.</p>`,
  },
  contact: {
    title: 'Contact NobleSeek',
    body: `<p>Email: <strong>support@fabrything.com</strong><br/>Phone: +880 1842-168117<br/>Address: Dhaka, Bangladesh</p><p>For corrections: send story URL + correct info; we update within 24h with an editor's note.</p><p>For ads/partnerships: mention NobleSeek in subject line.</p>`,
  },
  privacy: {
    title: 'Privacy Policy — NobleSeek',
    body: `<p>We use Google AdSense, Google Analytics 4 and Meta Pixel to measure readership and serve ads. These set cookies. You can block cookies in your browser; the site still works.</p><p>We never sell personal data. FB comments are governed by Meta's policy. Contact support@fabrything.com for data requests.</p>`,
  },
  disclaimer: {
    title: 'Disclaimer',
    body: `<p>NobleSeek reports on trending topics for information only. We verify with named sources; breaking stories are updated as facts arrive. Images carry credits; if you own one and want takedown/credit change, contact us.</p><p>Ads are clearly labelled and do not imply editorial endorsement.</p>`,
  },
  ethics: {
    title: 'Editorial Ethics',
    body: `<ul><li>Human review before every publish — AI drafts are scaffolds only.</li><li>No fabricated quotes, no clickbait without substance.</li><li>Corrections policy: fix + note at article bottom.</li><li>One hero image minimum, credited; no graphic content.</li><li>Separation of ads and editorial — advertisers don't approve copy.</li></ul>`,
  },
};

export default function NobleSeekInfoPage({ page = 'about' }) {
  const doc = DOCS[page] || DOCS.about;
  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <NewsSeo title={doc.title} description={doc.title} slug={page} />
      <Typography variant="h4" fontWeight={900} gutterBottom>{doc.title}</Typography>
      <Box dangerouslySetInnerHTML={{ __html: doc.body }} sx={{ '& p': { lineHeight: 1.8, mb: 1.5 } }} />
    </Container>
  );
}
