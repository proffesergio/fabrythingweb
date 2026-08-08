import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// The exact payload GET /api/store/banners/ returns in production (captured
// 2026-08-08). Note `data` is a FLAT list, not the nested {data:{data:[…]}}
// envelope the paginated list views use.
const LIVE_BANNERS = [
  {
    id: 1,
    image: 'https://fabrilife.com/images/homepage/monsoon-banner.jpg',
    eyebrow: '', headline: 'Shop Now', subtext: '',
    animation_style: 'FADE_UP', background: '#1a1a2e',
    cta_label: '', cta_link: null, display_order: 0,
  },
  {
    id: 2,
    image: 'https://www.arogga.com/_next/image?url=x&w=1280&q=75',
    eyebrow: '', headline: 'Buy Now', subtext: '',
    animation_style: 'FADE_UP', background: '#0f3460',
    cta_label: '', cta_link: null, display_order: 1,
  },
];

const mockUseCachedApi = jest.fn();
jest.mock('../../hooks/useCachedApi', () => ({
  __esModule: true,
  default: (...args) => mockUseCachedApi(...args),
}));

// Swiper is ESM inside node_modules (which CRA's Jest does not transform) and
// its package "exports" map is not resolvable by Jest either -- hence the
// moduleNameMapper in package.json, which makes these paths resolvable so they
// can be mocked here. Carousel mechanics are Swiper's concern; this file tests
// which slides HeroCarousel decides to render.
jest.mock('swiper/react', () => ({
  Swiper: ({ children }) => <div data-testid="swiper">{children}</div>,
  SwiperSlide: ({ children }) => <div>{children}</div>,
}));
jest.mock('swiper/modules', () => ({ Autoplay: {}, Pagination: {}, EffectFade: {} }));

import HeroCarousel from './HeroCarousel';

const renderHero = () => render(<MemoryRouter><HeroCarousel /></MemoryRouter>);
const FALLBACK_HEADLINE = 'Eid Collection 2026';

beforeEach(() => {
  mockUseCachedApi.mockReset();
});

test('renders the banners the owner configured', async () => {
  mockUseCachedApi.mockReturnValue({ data: LIVE_BANNERS, loading: false, error: null });
  renderHero();

  await waitFor(() => expect(screen.getByText('Shop Now')).toBeInTheDocument());
  expect(screen.getByText('Buy Now')).toBeInTheDocument();
  expect(screen.queryByText(FALLBACK_HEADLINE)).not.toBeInTheDocument();
});

test('falls back only when the fetch SUCCEEDED and returned nothing', async () => {
  mockUseCachedApi.mockReturnValue({ data: [], loading: false, error: null });
  renderHero();
  await waitFor(() => expect(screen.getByText(FALLBACK_HEADLINE)).toBeInTheDocument());
});

test('a failed fetch still shows a hero, but never blanks a configured one', async () => {
  // THE BUG THIS FILE EXISTS FOR. Render's free tier sleeps outside the
  // keep-warm window; a cold request produces no usable response, the old code
  // read that as an empty list, and the hero silently showed the built-in
  // placeholder slides -- the "same old hero that never updates".
  mockUseCachedApi.mockReturnValue({ data: null, loading: false, error: new Error('Network Error') });
  renderHero();
  await waitFor(() => expect(screen.getByText(FALLBACK_HEADLINE)).toBeInTheDocument());
});

test('keeps showing cached banners when a refresh fails', async () => {
  // stale-while-revalidate: useCachedApi hands back the last good payload and
  // reports the error separately, so a sleeping backend never downgrades a
  // configured hero to the placeholder slides.
  mockUseCachedApi.mockReturnValue({
    data: LIVE_BANNERS, loading: false, error: new Error('Network Error'),
  });
  renderHero();
  await waitFor(() => expect(screen.getByText('Shop Now')).toBeInTheDocument());
  expect(screen.queryByText(FALLBACK_HEADLINE)).not.toBeInTheDocument();
});

test('does not flash placeholder slides during the first load', async () => {
  mockUseCachedApi.mockReturnValue({ data: null, loading: true, error: null });
  renderHero();
  expect(screen.queryByText(FALLBACK_HEADLINE)).not.toBeInTheDocument();
  expect(screen.queryByText('Shop Now')).not.toBeInTheDocument();
});

test('reads the public banners endpoint through the caching hook', () => {
  mockUseCachedApi.mockReturnValue({ data: LIVE_BANNERS, loading: false, error: null });
  renderHero();
  expect(mockUseCachedApi).toHaveBeenCalledWith('store/banners/');
});
