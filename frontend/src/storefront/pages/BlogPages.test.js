import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import axios from 'axios';
import { BlogArticle, BlogIndex } from './BlogPages';

jest.mock('axios');
jest.mock('../../nobleseek/ads/AdSlot', () => () => null);
jest.mock('../../nobleseek/ads/adsConfig', () => ({ useAdConfig: () => ({}) }));

beforeEach(() => { jest.clearAllMocks(); window.scrollTo = jest.fn(); });

test('journal loads the next page without losing the archive route', async () => {
  axios.get.mockResolvedValueOnce({ data: { count: 2, next: 'next', results: [{ id: 1, slug: 'buying-guide', headline: 'A useful buying guide' }] } });
  axios.get.mockResolvedValueOnce({ data: { count: 2, next: null, results: [{ id: 2, slug: 'care-guide', headline: 'Care for your products' }] } });
  render(<MemoryRouter initialEntries={['/blog']}><BlogIndex /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'A useful buying guide' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /A useful buying guide/ })).toHaveAttribute('href', '/blog/buying-guide');
  fireEvent.click(screen.getByRole('button', { name: /page 2/i }));
  expect(await screen.findByRole('heading', { name: 'Care for your products' })).toBeInTheDocument();
  expect(axios.get).toHaveBeenLastCalledWith(expect.stringContaining('nobleseek/blog/'), { params: { page: 2 } });
});

test('article uses BlogPosting metadata and removes its schema on unmount', async () => {
  axios.get.mockResolvedValue({ data: { data: { slug: 'guide', headline: 'Choosing well', body_html: '<p>Useful advice.</p>', json_ld: { '@type': 'BlogPosting', headline: 'Choosing well' } } } });
  const view = render(<MemoryRouter initialEntries={['/blog/guide']}><Routes><Route path="/blog/:slug" element={<BlogArticle />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Choosing well' })).toBeInTheDocument();
  await waitFor(() => expect(document.querySelector('script[type="application/ld+json"]')).toHaveTextContent('BlogPosting'));
  expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute('href', 'https://www.fabrything.com/blog/guide');
  view.unmount();
  expect(document.querySelector('script[type="application/ld+json"]')).toBeNull();
});

test('missing article receives noindex and a journal return link', async () => {
  axios.get.mockRejectedValue({ response: { status: 404 } });
  render(<MemoryRouter initialEntries={['/blog/missing']}><Routes><Route path="/blog/:slug" element={<BlogArticle />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Story not found' })).toBeInTheDocument();
  await waitFor(() => expect(document.querySelector('meta[name="robots"]')).toHaveAttribute('content', 'noindex,follow'));
  expect(screen.getByRole('link', { name: 'Back to the journal' })).toHaveAttribute('href', '/blog');
});
