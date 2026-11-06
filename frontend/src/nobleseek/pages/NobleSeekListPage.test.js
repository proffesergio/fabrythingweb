import React from 'react';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import NobleSeekListPage from './NobleSeekListPage';
import { fetchNewsList, fetchNewsCategories, fetchSection, fetchPopular, fetchPolls } from '../api';

jest.mock('../api', () => ({ ...jest.requireActual('../api'), fetchNewsList: jest.fn(), fetchNewsCategories: jest.fn(), fetchSection: jest.fn(), fetchPopular: jest.fn(), fetchPolls: jest.fn() }));
jest.mock('../components/NewsSeo', () => () => null);
jest.mock('../portal/PortalHeader', () => ({ NS_ACCENT: '#F2631F' }));
jest.mock('../ads/adsConfig', () => ({ useAdConfig: () => ({}) }));
jest.mock('../ads/AdSlot', () => ({ placement }) => <aside aria-label={`ad ${placement}`} />);

const story = (id) => ({ id, slug: `report-${id}`, headline: `API report ${id}`, hero_image: `https://news.example/${id}.jpg`, hero_image_alt: `API photo ${id}` });
const deferred = () => { let resolve; let reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
let navigate;
function Harness() { navigate = useNavigate(); return <NobleSeekListPage />; }
function mount(path = '/nobleseek') { return render(<MemoryRouter initialEntries={[path]}><Harness /></MemoryRouter>); }
beforeEach(() => {
  jest.clearAllMocks();
  fetchNewsCategories.mockResolvedValue([]);
  fetchNewsList.mockResolvedValue({ results: [], count: 0 });
  fetchSection.mockResolvedValue([]);
  fetchPopular.mockResolvedValue([]);
  fetchPolls.mockResolvedValue([]);
});

test('renders API lead, image, sections, poll and archive link without draft content', async () => {
  fetchNewsList.mockResolvedValue({ results: Array.from({ length: 7 }, (_, i) => story(i + 1)), count: 37 });
  fetchSection.mockImplementation(async (category) => category === 'sports' ? [story(20)] : []);
  fetchPolls.mockResolvedValue([{ id: 1, question: 'API poll question', options: [{ id: 2, text: 'API option', votes: 0 }] }]);
  const { container } = mount();
  expect(await screen.findByRole('heading', { level: 1, name: 'API report 1' })).toBeInTheDocument();
  expect(await screen.findByRole('heading', { name: 'API report 20' })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'সর্বশেষ (37টি খবর)' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'সব খবর →' })).toHaveAttribute('href', '/nobleseek?search=');
  expect(screen.getByRole('link', { name: 'ফেসবুকে আমাদের অনুসরণ করুন' })).toHaveAttribute('href', 'https://www.facebook.com/nobleseek');
  expect(await screen.findByText('API poll question')).toBeInTheDocument();
  expect(screen.getByRole('img', { name: 'API photo 1' })).toHaveAttribute('src', 'https://news.example/1.jpg');
  expect(container.innerHTML).not.toMatch(/supabase|nobleseek-current\.png/);
  expect(screen.queryByRole('heading', { name: 'মতামত' })).not.toBeInTheDocument();
});

test('empty API data shows honest empty states and omits empty section rows', async () => {
  mount();
  expect(await screen.findByRole('heading', { level: 1, name: 'এখনো কোনো খবর প্রকাশ হয়নি' })).toBeInTheDocument();
  expect(screen.queryByRole('region', { name: 'খেলা' })).not.toBeInTheDocument();
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(screen.queryByText('আজকের জরিপ')).not.toBeInTheDocument();
});

test('homepage request failure offers retry instead of claiming no published news', async () => {
  fetchNewsList.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ results: [story(8)], count: 1 });
  mount();
  const alert = await screen.findByRole('alert');
  expect(screen.queryByRole('heading', { name: 'এখনো কোনো খবর প্রকাশ হয়নি' })).not.toBeInTheDocument();
  fireEvent.click(within(alert).getByRole('button', { name: 'আবার চেষ্টা করুন' }));
  expect(await screen.findByRole('heading', { level: 1, name: 'API report 8' })).toBeInTheDocument();
});

test.each([
  ['/nobleseek?category=sports', '/nobleseek?category=world'],
  ['/nobleseek?search=old', '/nobleseek?search=new'],
])('late response from %s cannot replace %s', async (first, second) => {
  const old = deferred();
  fetchNewsList.mockReturnValueOnce(old.promise).mockResolvedValueOnce({ results: [story(2)], count: 1 });
  mount(first);
  await act(async () => navigate(second));
  expect(await screen.findAllByRole('heading', { name: 'API report 2' })).toHaveLength(2);
  await act(async () => old.resolve({ results: [story(1)], count: 999 }));
  expect(screen.queryByRole('heading', { name: 'API report 1' })).not.toBeInTheDocument();
  expect(screen.getByText('1টি খবর পাওয়া গেছে')).toBeInTheDocument();
});

test('pending pagination cannot append articles into another category', async () => {
  const more = deferred();
  fetchNewsList.mockResolvedValueOnce({ results: [story(1)], count: 2 }).mockReturnValueOnce(more.promise).mockResolvedValueOnce({ results: [story(3)], count: 1 });
  mount('/nobleseek?category=sports');
  fireEvent.click(await screen.findByRole('button', { name: 'আরও খবর লোড করুন' }));
  await act(async () => navigate('/nobleseek?category=world'));
  await screen.findAllByRole('heading', { name: 'API report 3' });
  await act(async () => more.resolve({ results: [story(2)], count: 2 }));
  expect(screen.queryByRole('heading', { name: 'API report 2' })).not.toBeInTheDocument();
});

test('failed pagination retries the same page and retains existing articles', async () => {
  fetchNewsList.mockResolvedValueOnce({ results: [story(1)], count: 2 }).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ results: [story(2)], count: 2 });
  mount('/nobleseek?search=');
  fireEvent.click(await screen.findByRole('button', { name: 'আরও খবর লোড করুন' }));
  const alert = await screen.findByRole('alert');
  expect(screen.getAllByRole('heading', { name: 'API report 1' })).toHaveLength(2);
  fireEvent.click(within(alert).getByRole('button', { name: 'আবার চেষ্টা করুন' }));
  await screen.findAllByRole('heading', { name: 'API report 2' });
  expect(fetchNewsList.mock.calls.map(([args]) => args.page)).toEqual([1, 2, 2]);
  expect(screen.queryByRole('button', { name: 'আরও খবর লোড করুন' })).not.toBeInTheDocument();
});

test('category API failure retains catalog labels and an empty listing can return home', async () => {
  fetchNewsCategories.mockRejectedValue(new Error('offline'));
  mount('/nobleseek?category=world');
  expect(await screen.findByRole('heading', { level: 1, name: 'আন্তর্জাতিক' })).toBeInTheDocument();
  expect(await screen.findByRole('link', { name: 'প্রচ্ছদে ফিরুন' })).toHaveAttribute('href', '/nobleseek');
  expect(screen.getByText('0টি খবর পাওয়া গেছে')).toBeInTheDocument();
});

test('a failed first page reports failure and can be retried without an empty-news claim', async () => {
  fetchNewsList.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ results: [story(8)], count: 1 });
  mount('/nobleseek?search=query');
  const alert = await screen.findByRole('alert');
  expect(screen.queryByRole('link', { name: 'প্রচ্ছদে ফিরুন' })).not.toBeInTheDocument();
  fireEvent.click(within(alert).getByRole('button', { name: 'আবার চেষ্টা করুন' }));
  expect(await screen.findAllByRole('heading', { name: 'API report 8' })).toHaveLength(2);
});
