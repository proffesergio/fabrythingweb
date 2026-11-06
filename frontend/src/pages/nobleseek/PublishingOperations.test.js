import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PublishingOperations, { formatBytes, policyErrors, storageForecast } from './PublishingOperations';

const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi }));

const policy = {
  news_site_url: 'https://news.example.com', ingestion_paused: false,
  daily_article_limit: 0, require_review_for_automation: false,
  estimated_text_bytes_per_article: 20000, estimated_image_bytes_per_article: 200000,
};
const operations = {
  generated_at: '2026-11-07T10:00:00Z',
  counts: { total: 128, news: 120, blog: 8, drafts: 5, review: 1, published: 120, scheduled: 2, archived: 0, created_today: 7, total_views: 6000 },
  production_last_24h: { created: 17, news_created: 15, blog_created: 2, published: 11 },
  seo: {
    articles_with_missing_metadata: 1, missing: { seo_title: 1, seo_description: 0, hero_image: 0, hero_image_alt: 1 },
    sample_limit: 10, samples: [{ id: 41, slug: 'article-to-fix', headline: 'Article to fix', content_type: 'NEWS', missing_fields: ['seo_title', 'hero_image_alt'] }],
  },
  database: { vendor: 'postgresql', available: true, size_bytes: 1048576 },
  provider_metrics: { available: false, reason: 'Provider usage, quotas, and billing are not connected.', storage_limit_bytes: null, requests: null, cost: null },
  storage_estimate: { total_bytes: 800000, text_bytes: 200000, image_bytes: 600000, assumptions: { note: 'Excludes indexes and backups. Images may be external.' } },
};
const ok = (data) => ({ status: 200, data: { data } });
beforeEach(() => {
  mockCallApi.mockReset();
  mockCallApi.mockImplementation(async ({ url, method, body }) => {
    if (method === 'PATCH') return ok(body);
    return ok(url.endsWith('publishing-settings/') ? policy : operations);
  });
});

it('uses measured data, opens real audit items, and never invents provider health', async () => {
  const onEditArticle = jest.fn();
  const onShowArticles = jest.fn();
  render(<PublishingOperations onEditArticle={onEditArticle} onShowArticles={onShowArticles} />);
  expect(await screen.findByText('Article to fix')).toBeInTheDocument();
  expect(screen.getByText('120')).toBeInTheDocument();
  expect(screen.getByText('17')).toBeInTheDocument();
  expect(screen.getByText('1.00 MiB')).toBeInTheDocument();
  expect(screen.getByText(/Provider usage, quotas, and billing are not connected/)).toBeInTheDocument();
  expect(screen.queryByText(/system operational|sample data mode|connect accounts/i)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Open in editor' }));
  expect(onEditArticle).toHaveBeenCalledWith(41);
  fireEvent.click(screen.getByRole('button', { name: 'Manage blog' }));
  expect(onShowArticles).toHaveBeenCalledWith('BLOG');
});

it('previews byte changes without writing and saves validated policy through the JWT API hook', async () => {
  render(<PublishingOperations />);
  const bytes = await screen.findByLabelText('Text bytes per article');
  fireEvent.change(bytes, { target: { value: '30000' } });
  fireEvent.change(screen.getByLabelText('Daily article cap'), { target: { value: '20' } });
  fireEvent.click(screen.getByLabelText(/Pause new article creation/));
  expect(screen.getByText(/preview using unsaved assumptions/)).toBeInTheDocument();
  expect(mockCallApi.mock.calls.filter(([args]) => args.method === 'PATCH')).toHaveLength(0);
  fireEvent.click(screen.getByRole('button', { name: 'Save settings' }));
  await screen.findByText('Publishing settings saved.');
  expect(mockCallApi).toHaveBeenCalledWith(expect.objectContaining({
    url: 'store/nobleseek/admin/publishing-settings/', method: 'PATCH',
    body: { ...policy, daily_article_limit: 20, ingestion_paused: true, estimated_text_bytes_per_article: 30000 },
    timeout: 25000, rawError: true,
  }));
  expect(screen.getByRole('button', { name: 'Save settings' })).toBeDisabled();
});

it('retains edits after server rejection and after metrics refresh', async () => {
  mockCallApi.mockImplementation(async ({ url, method }) => {
    if (method === 'PATCH') return { status: 400, data: { daily_article_limit: ['Rejected by server.'] } };
    return ok(url.endsWith('publishing-settings/') ? policy : operations);
  });
  render(<PublishingOperations />);
  const cap = await screen.findByLabelText('Daily article cap');
  fireEvent.change(cap, { target: { value: '33' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save settings' }));
  await screen.findByText(/Rejected by server/);
  expect(cap).toHaveValue(33);
  fireEvent.click(screen.getByRole('button', { name: 'Refresh metrics' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Refresh metrics' })).toBeEnabled());
  expect(cap).toHaveValue(33);
  expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
});

it('keeps policy editable when operations fail and identifies missing measurements', async () => {
  mockCallApi.mockImplementation(async ({ url }) => url.endsWith('publishing-settings/') ? ok(policy) : null);
  render(<PublishingOperations />);
  expect(await screen.findByLabelText('Canonical news origin')).toHaveValue(policy.news_site_url);
  expect(await screen.findByText(/No measurements are available/)).toBeInTheDocument();
  expect(screen.queryByText('0')).not.toBeInTheDocument();
  expect(screen.getByText('Audit unavailable until operations data loads.')).toBeInTheDocument();
});

it('shows staff denial and offers retry without a writable default policy', async () => {
  mockCallApi.mockResolvedValue({ status: 403, data: {} });
  render(<PublishingOperations />);
  await screen.findAllByText(/Staff access required/);
  expect(screen.queryByRole('button', { name: 'Save settings' })).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Canonical news origin')).not.toBeInTheDocument();
});

it('rejects invalid policy and calculates explicit 20/day forecasts', () => {
  expect(policyErrors(policy)).toEqual({});
  expect(policyErrors({ ...policy, news_site_url: 'https://news.example.com/path', daily_article_limit: '-1' })).toHaveProperty('news_site_url');
  expect(policyErrors({ ...policy, estimated_text_bytes_per_article: '1.5' })).toHaveProperty('estimated_text_bytes_per_article');
  expect(policyErrors({ ...policy, estimated_image_bytes_per_article: '' })).toHaveProperty('estimated_image_bytes_per_article');
  expect(storageForecast(20000, 200000, 365)).toBe(1606000000);
  expect(storageForecast(20000, 200000, 30)).toBe(132000000);
  expect(storageForecast('', 200000, 30)).toBeNull();
  expect(formatBytes(null)).toBe('Unavailable');
  expect(formatBytes(0)).toBe('0 B');
});
