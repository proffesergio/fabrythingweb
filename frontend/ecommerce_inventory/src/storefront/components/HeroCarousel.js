import React, { useEffect, useState } from 'react';
import { Box, Typography, Button, Container, Chip, GlobalStyles } from '@mui/material';
import { ArrowForward } from '@mui/icons-material';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Autoplay, Pagination, EffectFade } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/pagination';
import 'swiper/css/effect-fade';
import useCachedApi from '../../hooks/useCachedApi';

// Static fallback shown when the owner hasn't configured any banners yet
// (GET /api/store/banners/ returns an empty list) -- keeps the homepage from
// ever rendering an empty hero.
const FALLBACK_SLIDES = [
    {
        title: 'Eid Collection 2026',
        subtitle: 'Discover premium Panjabis, Sarees & festive wear for the whole family',
        cta: 'Shop Eid Collection',
        link: '/shop',
        image: 'https://picsum.photos/seed/eid_fashion/1600/700',
        overlay: 'linear-gradient(135deg, rgba(26,26,46,0.82) 0%, rgba(15,52,96,0.72) 100%)',
    },
    {
        title: 'Summer Sale — Up to 50% Off',
        subtitle: 'Limited time offer on selected men\'s, women\'s & kids\' styles.',
        cta: 'Shop the Sale',
        link: '/shop?ordering=price_low',
        image: 'https://picsum.photos/seed/summer_sale/1600/700',
        overlay: 'linear-gradient(135deg, rgba(232,93,74,0.80) 0%, rgba(192,57,43,0.70) 100%)',
    },
    {
        title: 'New Arrivals Every Week',
        subtitle: 'Fresh styles added constantly. Stay ahead of the trends.',
        cta: 'See What\'s New',
        link: '/shop?ordering=newest',
        image: 'https://picsum.photos/seed/new_arrivals/1600/700',
        overlay: 'linear-gradient(135deg, rgba(45,45,45,0.82) 0%, rgba(99,99,99,0.72) 100%)',
    },
    {
        title: 'Free Delivery Nationwide',
        subtitle: 'Fast delivery nationwide. Cash on Delivery available.',
        cta: 'Start Shopping',
        link: '/shop',
        image: 'https://picsum.photos/seed/delivery_fashion/1600/700',
        overlay: 'linear-gradient(135deg, rgba(27,94,32,0.82) 0%, rgba(56,142,60,0.72) 100%)',
    },
];

// Maps Banner.animation_style (backend enum) to the CSS class the global
// keyframes below key off of. Applied to the product cut-out image only --
// the text column has its own gentler, un-timed entrance.
const ANIMATION_CLASS = {
    FADE_UP: 'banner-anim-fade-up',
    SLIDE_IN: 'banner-anim-slide-in',
    FLOAT: 'banner-anim-float',
    ZOOM: 'banner-anim-zoom',
};

function isInternalLink(link) {
    return typeof link === 'string' && link.startsWith('/');
}

function CtaButton({ label, link, ...props }) {
    if (!link) return null;
    return isInternalLink(link) ? (
        <Button component={Link} to={link} {...props}>{label}</Button>
    ) : (
        <Button component="a" href={link} target="_blank" rel="noopener noreferrer" {...props}>{label}</Button>
    );
}

// Renders one banner-driven slide: configurable background (colour/gradient)
// behind a transparent PNG product cut-out, with the chosen animation preset
// applied to the cut-out only -- text/CTA fade in without competing motion.
function BannerSlide({ banner }) {
    return (
        <Box
            sx={{
                position: 'relative',
                color: 'white',
                py: { xs: 6, md: 10 },
                minHeight: { xs: 320, md: 440 },
                display: 'flex',
                alignItems: 'center',
                overflow: 'hidden',
                background: banner.background_color || banner.background || '#1a1a2e',
            }}
        >
            <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 2, width: '100%' }}>
                <Box sx={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    flexDirection: { xs: 'column', md: 'row' }, gap: { xs: 3, md: 4 }, textAlign: { xs: 'center', md: 'left' },
                }}>
                    <Box sx={{ maxWidth: 520 }}>
                        {banner.eyebrow && (
                            <Chip
                                label={banner.eyebrow}
                                size="small"
                                sx={{ mb: 1.5, bgcolor: 'rgba(255,255,255,0.18)', color: 'white', fontWeight: 700 }}
                            />
                        )}
                        <Typography
                            variant="h2"
                            sx={{
                                fontWeight: 800, mb: 2,
                                fontSize: { xs: '1.75rem', sm: '2.25rem', md: '3rem' },
                                textShadow: '0 2px 20px rgba(0,0,0,0.3)', letterSpacing: '-1px',
                            }}
                        >
                            {banner.title}
                        </Typography>
                        {banner.subtitle && (
                            <Typography variant="h6" sx={{
                                color: 'rgba(255,255,255,0.85)', mb: 3, fontWeight: 400,
                                fontSize: { xs: '0.9rem', md: '1.15rem' },
                            }}>
                                {banner.subtitle}
                            </Typography>
                        )}
                        <CtaButton
                            label={banner.cta} link={banner.link}
                            variant="contained" size="large" endIcon={<ArrowForward />}
                            sx={{
                                bgcolor: 'white', color: '#2D2D2D', fontWeight: 700,
                                px: 4, py: 1.5, borderRadius: 3, fontSize: '1rem',
                                '&:hover': { bgcolor: 'rgba(255,255,255,0.9)', transform: 'translateY(-2px)', boxShadow: '0 8px 25px rgba(0,0,0,0.3)' },
                                transition: 'all 0.3s ease',
                            }}
                        />
                    </Box>

                    {banner.image && (
                        <Box
                            component="img"
                            src={banner.image}
                            alt=""
                            aria-hidden="true"
                            className={`banner-product-img ${ANIMATION_CLASS[banner.animationStyle] || ''}`}
                            sx={{
                                width: { xs: '60%', sm: '45%', md: 320 },
                                maxWidth: 360,
                                filter: 'drop-shadow(0 20px 30px rgba(0,0,0,0.35))',
                                objectFit: 'contain',
                            }}
                        />
                    )}
                </Box>
            </Container>
        </Box>
    );
}

// The pre-existing hardcoded promo carousel, kept verbatim as the fallback
// when no banners are configured.
function FallbackSlide({ slide }) {
    return (
        <Box
            sx={{
                position: 'relative',
                color: 'white',
                py: { xs: 8, md: 14 },
                textAlign: 'center',
                overflow: 'hidden',
                minHeight: { xs: 280, md: 420 },
                display: 'flex',
                alignItems: 'center',
                '&::after': {
                    content: '""', position: 'absolute', inset: 0,
                    backgroundImage: `url(${slide.image})`, backgroundSize: 'cover', backgroundPosition: 'center', zIndex: 0,
                },
                '&::before': {
                    content: '""', position: 'absolute', inset: 0,
                    backgroundImage: slide.overlay, zIndex: 1,
                },
            }}
        >
            <Container maxWidth="md" sx={{ position: 'relative', zIndex: 2, width: '100%' }}>
                <Typography
                    variant="h2"
                    sx={{
                        fontWeight: 800, mb: 2,
                        fontSize: { xs: '2rem', sm: '2.5rem', md: '3.5rem' },
                        textShadow: '0 2px 20px rgba(0,0,0,0.3)', letterSpacing: '-1px',
                    }}
                >
                    {slide.title}
                </Typography>
                <Typography
                    variant="h6"
                    sx={{
                        color: 'rgba(255,255,255,0.85)', mb: 4, fontWeight: 400,
                        fontSize: { xs: '0.95rem', md: '1.25rem' }, maxWidth: 600, mx: 'auto',
                    }}
                >
                    {slide.subtitle}
                </Typography>
                <CtaButton
                    label={slide.cta} link={slide.link}
                    variant="contained" size="large" endIcon={<ArrowForward />}
                    sx={{
                        bgcolor: 'white', color: '#2D2D2D', fontWeight: 700,
                        px: 4, py: 1.5, borderRadius: 3, fontSize: '1rem',
                        '&:hover': { bgcolor: 'rgba(255,255,255,0.9)', transform: 'translateY(-2px)', boxShadow: '0 8px 25px rgba(0,0,0,0.3)' },
                        transition: 'all 0.3s ease',
                    }}
                />
            </Container>
        </Box>
    );
}

// Global keyframes for the four animation presets, keyed to `.swiper-slide-active`
// so the entrance replays every time a banner slide becomes the active one (a
// plain CSS animation on mount would only ever play once for a looped
// carousel, since Swiper doesn't remount slides on transition). All four are
// disabled under prefers-reduced-motion.
function BannerAnimationStyles() {
    return (
        <GlobalStyles styles={{
            '@keyframes bannerAnimFadeUp': {
                '0%': { opacity: 0, transform: 'translateY(28px)' },
                '100%': { opacity: 1, transform: 'translateY(0)' },
            },
            '@keyframes bannerAnimSlideIn': {
                '0%': { opacity: 0, transform: 'translateX(60px)' },
                '100%': { opacity: 1, transform: 'translateX(0)' },
            },
            '@keyframes bannerAnimZoom': {
                '0%': { opacity: 0, transform: 'scale(0.75)' },
                '100%': { opacity: 1, transform: 'scale(1)' },
            },
            '@keyframes bannerAnimFloat': {
                '0%, 100%': { transform: 'translateY(0)' },
                '50%': { transform: 'translateY(-14px)' },
            },
            '.swiper-slide:not(.swiper-slide-active) .banner-product-img': { opacity: 0 },
            '.swiper-slide-active .banner-anim-fade-up': { animation: 'bannerAnimFadeUp 0.9s ease-out both' },
            '.swiper-slide-active .banner-anim-slide-in': { animation: 'bannerAnimSlideIn 0.9s ease-out both' },
            '.swiper-slide-active .banner-anim-zoom': { animation: 'bannerAnimZoom 0.9s ease-out both' },
            '.swiper-slide-active .banner-anim-float': {
                opacity: 1,
                animation: 'bannerAnimFloat 3.6s ease-in-out 0.9s infinite',
            },
            '@media (prefers-reduced-motion: reduce)': {
                '.swiper-slide:not(.swiper-slide-active) .banner-product-img': { opacity: 1 },
                '.banner-anim-fade-up, .banner-anim-slide-in, .banner-anim-zoom, .banner-anim-float': {
                    animation: 'none', opacity: 1, transform: 'none',
                },
            },
        }} />
    );
}

export default function HeroCarousel() {
    // Stale-while-revalidate, deliberately NOT a plain callApi.
    //
    // callApi resolves to `null` on any failure, and the old code did
    // `res?.data?.data || []` -- so a request that never completed was
    // indistinguishable from "the owner has configured no banners", and the
    // hero silently dropped to the built-in placeholder slides. Render's free
    // tier sleeps outside the keep-warm window (09:00-01:00 Dhaka), and a cold
    // request is answered by Render's edge with no CORS headers, which the
    // browser blocks. The result was a homepage that showed stock "Eid
    // Collection" slides no matter what the admin panel said.
    //
    // useCachedApi keeps the last good payload on failure and reports the
    // error separately, so a sleeping backend can no longer downgrade a
    // configured hero -- and a returning visitor paints their real banners
    // instantly from cache instead of waiting on a cold boot.
    const { data, loading } = useCachedApi('store/banners/');
    const banners = Array.isArray(data) ? data : null;

    const usingBanners = Array.isArray(banners) && banners.length > 0;
    const slides = usingBanners
        ? banners.map((b) => ({
            id: b.id,
            title: b.headline,
            subtitle: b.subtext,
            eyebrow: b.eyebrow,
            cta: b.cta_label,
            link: b.cta_link,
            image: b.image,
            background: b.background,
            animationStyle: b.animation_style,
        }))
        : FALLBACK_SLIDES;

    // Nothing to show yet: render an empty band of the right height rather
    // than a flash of placeholder slides that the real banners then replace.
    if (loading && banners === null) {
        return <Box sx={{ minHeight: { xs: 320, md: 440 }, bgcolor: '#1a1a2e' }} />;
    }

    return (
        <Box sx={{ position: 'relative' }}>
            <BannerAnimationStyles />
            <Swiper
                modules={[Autoplay, Pagination, EffectFade]}
                effect="fade"
                autoplay={{ delay: 4500, disableOnInteraction: false }}
                pagination={{ clickable: true }}
                loop
                style={{ '--swiper-pagination-color': '#E85D4A', '--swiper-pagination-bullet-inactive-color': '#fff' }}
            >
                {slides.map((slide, i) => (
                    <SwiperSlide key={usingBanners ? slide.id : i}>
                        {usingBanners ? <BannerSlide banner={slide} /> : <FallbackSlide slide={slide} />}
                    </SwiperSlide>
                ))}
            </Swiper>
        </Box>
    );
}
