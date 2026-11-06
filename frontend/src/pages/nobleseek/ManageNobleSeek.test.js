import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ManageNobleSeek from './ManageNobleSeek';

const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi }));
jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('./tabs/DeskHome', () => () => null);
jest.mock('./tabs/TagsManager', () => () => null);
jest.mock('./tabs/PagesManager', () => () => null);
jest.mock('./tabs/CommentsManager', () => () => null);
jest.mock('./tabs/PushManager', () => () => null);
jest.mock('./tabs/PollsManager', () => () => null);
jest.mock('./ShareMenu', () => () => null);
jest.mock('./PublishingOperations', () => ({ onEditArticle, onShowArticles }) => <div>
  <button onClick={() => onEditArticle(41)}>Fix metadata</button>
  <button onClick={() => onShowArticles('BLOG')}>Manage blog</button>
</div>);

beforeEach(() => {
  localStorage.clear();
  mockCallApi.mockReset();
  mockCallApi.mockImplementation(async ({ url, method }) => {
    if (url.endsWith('/articles/41/')) return { status: 200, data: { id: 41, content_type: 'BLOG', headline: 'Existing guide', slug: 'existing-guide', body_html: '<p>Guide body</p>', status: 'DRAFT' } };
    if (method === 'POST') return { status: 201, data: {} };
    return { status: 200, data: { data: url.endsWith('/stats/') || url.endsWith('/ad-config/') ? {} : [] } };
  });
});
function mount(tab) {
  return render(<MemoryRouter initialEntries={[`/admin/manage/nobleseek?tab=${tab}`]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><ManageNobleSeek /></MemoryRouter>);
}

it('opens the operations deep link and filters blog server-side before pagination', async () => {
  mount('operations');
  await waitFor(() => expect(screen.getByRole('button', { name: 'রিলোড' })).toBeEnabled());
  expect(screen.getByRole('tab', { name: 'SEO & operations' })).toHaveAttribute('aria-selected', 'true');
  fireEvent.click(screen.getByRole('button', { name: 'Manage blog' }));
  await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith(expect.objectContaining({
    url: 'store/nobleseek/admin/articles/', params: expect.objectContaining({ content_type: 'BLOG', pageSize: 100 }),
  })));
  expect(screen.getByLabelText('Content type')).toHaveTextContent('Blog');
  await waitFor(() => expect(screen.getByRole('button', { name: 'রিলোড' })).toBeEnabled());
});

it('loads an audit article from the unwrapped DRF detail and preserves its blog type on save', async () => {
  mount('seo');
  fireEvent.click(await screen.findByRole('button', { name: 'Fix metadata' }));
  const dialog = await screen.findByRole('dialog');
  expect(within(dialog).getByLabelText('Content type')).toHaveTextContent('Blog / product guide');
  expect(within(dialog).getByRole('link', { name: 'প্রিভিউ' })).toHaveAttribute('href', '/blog/existing-guide');
  fireEvent.click(within(dialog).getByRole('button', { name: 'খসড়া রাখুন' }));
  await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith(expect.objectContaining({
    url: 'store/nobleseek/admin/articles/41/', method: 'PATCH', body: expect.objectContaining({ content_type: 'BLOG', headline: 'Existing guide' }),
  })));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  await waitFor(() => expect(screen.getByRole('button', { name: 'রিলোড' })).toBeEnabled());
});
