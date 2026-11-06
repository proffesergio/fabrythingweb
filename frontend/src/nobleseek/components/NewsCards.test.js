import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LeadCard, NewsImage } from './NewsCards';
import MostRead from './MostRead';
import { fetchPopular } from '../api';
jest.mock('../api', () => ({ ...jest.requireActual('../api'), fetchPopular: jest.fn() }));
jest.mock('../portal/PortalHeader', () => ({ NS_ACCENT: '#F2631F' }));

beforeEach(() => fetchPopular.mockResolvedValue([]));
test('lead headline follows the real API image and keeps the article route', () => {
  const article = { slug: 'api-story', headline: 'API headline', headline_bn: 'বাংলা শিরোনাম', hero_image: 'https://news.example/photo.jpg', hero_image_alt: 'API image description' };
  render(<MemoryRouter><LeadCard article={article} /></MemoryRouter>);
  const image = screen.getByRole('img', { name: 'API image description' });
  const heading = screen.getByRole('heading', { level: 1, name: 'বাংলা শিরোনাম' });
  expect(image.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByRole('link')).toHaveAttribute('href', expect.stringContaining('/nobleseek/api-story?'));
  expect(screen.getAllByRole('img')).toHaveLength(1);
});
test('missing and failed images use a neutral fallback and recover for a new URL', () => {
  const { rerender } = render(<NewsImage />);
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(screen.getByText('নোবেলসিক')).toBeInTheDocument();
  rerender(<NewsImage src="https://news.example/broken.jpg" alt="Real photo" />);
  fireEvent.error(screen.getByRole('img', { name: 'Real photo' }));
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  rerender(<NewsImage src="https://news.example/new.jpg" alt="New photo" />);
  expect(screen.getByRole('img', { name: 'New photo' })).toHaveAttribute('src', 'https://news.example/new.jpg');
});
test('latest and popular keep distinct real API data with accessible tab panels', async () => {
  fetchPopular.mockResolvedValue([{ slug: 'popular', headline: 'Popular API story' }]);
  render(<MemoryRouter><MostRead latest={[]} /></MemoryRouter>);
  expect(screen.getByRole('tabpanel')).toHaveTextContent('কোনো খবর পাওয়া যায়নি');
  fireEvent.click(screen.getByRole('tab', { name: 'সর্বাধিক পঠিত' }));
  expect(await screen.findByRole('heading', { name: 'Popular API story' })).toBeInTheDocument();
  expect(screen.getByRole('tabpanel')).toHaveAccessibleName('সর্বাধিক পঠিত');
  fireEvent.click(screen.getByRole('tab', { name: 'সর্বশেষ' }));
  expect(screen.queryByText('Popular API story')).not.toBeInTheDocument();
  expect(screen.getByRole('tabpanel')).toHaveTextContent('কোনো খবর পাওয়া যায়নি');
});
