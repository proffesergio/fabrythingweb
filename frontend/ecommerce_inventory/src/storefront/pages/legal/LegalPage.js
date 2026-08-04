import React, { useEffect } from 'react';
import { Box, Container, Divider, Link as MuiLink, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import { LAST_UPDATED, LEGAL_PAGES, SUPPORT } from './content';

/**
 * One layout for every policy page. The content lives in ./content.js so the
 * policies stay in a single editable place and can never drift apart in tone
 * or last-updated date.
 *
 * `doc` is one of the exports from content.js. Each page gets its own route so
 * it has a stable public URL — Google Play and the App Store both require a
 * publicly reachable privacy policy URL, and it must not be behind a login.
 */
export default function LegalPage({ doc }) {
    useEffect(() => {
        document.title = `${doc.title} — Fabrything`;
    }, [doc.title]);

    return (
        <Container maxWidth="md" sx={{ py: { xs: 4, md: 6 } }}>
            <Typography variant="h4" component="h1" fontWeight={800} gutterBottom>
                {doc.title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Last updated {LAST_UPDATED}
            </Typography>

            <Typography variant="body1" sx={{ mb: 4 }}>
                {doc.intro}
            </Typography>

            {doc.sections.map((section) => (
                <Box key={section.h} component="section" sx={{ mb: 4 }}>
                    <Typography variant="h6" component="h2" fontWeight={700} gutterBottom>
                        {section.h}
                    </Typography>
                    {section.body.map((paragraph, i) => (
                        <Typography
                            key={i}
                            variant="body1"
                            component="p"
                            sx={{ mb: 1.5, color: 'text.secondary', lineHeight: 1.7 }}
                        >
                            {paragraph}
                        </Typography>
                    ))}
                </Box>
            ))}

            <Divider sx={{ my: 4 }} />

            <Typography variant="h6" component="h2" fontWeight={700} gutterBottom>
                Contact us
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary', mb: 0.5 }}>
                Email: <MuiLink href={`mailto:${SUPPORT.email}`}>{SUPPORT.email}</MuiLink>
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary', mb: 0.5 }}>
                WhatsApp:{' '}
                <MuiLink
                    href={`https://wa.me/${SUPPORT.whatsapp.replace(/[^0-9]/g, '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    {SUPPORT.whatsapp}
                </MuiLink>
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary', mb: 3 }}>
                {SUPPORT.entity} — {SUPPORT.address}
            </Typography>

            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                {LEGAL_PAGES.filter((p) => p.slug !== doc.slug).map((p) => (
                    <MuiLink key={p.slug} component={Link} to={`/${p.slug}`} variant="body2">
                        {p.title}
                    </MuiLink>
                ))}
            </Box>
        </Container>
    );
}
