import { render, screen, waitFor, fireEvent } from '@testing-library/react';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));

const mockCalls = [];
let mockSearchResult = null;
let mockBulkAddResult = null;
let mockListResult = null;

const categoryTree = [
    { id: 10, slug: 'beauty-health', name: 'Beauty & Health', children: [] },
];

const candidate = {
    source_url: 'https://www.rokomari.com/product/531074/perfume-a',
    name: 'Perfume A', price: 590, discount_price: 554,
    images: ['https://rokbucket.rokomari.io/x/full.jpg'], already_have: false,
    remote_product_id: '531074',
};

const affiliateProduct = {
    id: 1, program: 'rokomari', title: 'Perfume A', brand: 'Brand', image: '/api/media/a/',
    original_price: '590.00', current_price: '554.00', link_type: 'CART',
    manual_short_link: '', is_active: true, starts_at: null, ends_at: null,
    display_order: 0, click_count: 3, show_in_sidebar: true, show_on_deals_page: false,
    show_in_category_grid: false, grid_category_ids: [],
};

jest.mock('../../hooks/APIHandler', () => () => ({
    loading: false,
    error: '',
    callApi: async (opts) => {
        mockCalls.push(opts);
        if (opts.url === 'products/categories/') {
            return { status: 200, data: { data: { data: categoryTree } } };
        }
        if (opts.url === 'store/admin/affiliate/search/') return mockSearchResult;
        if (opts.url === 'store/admin/affiliate/bulk-add/') return mockBulkAddResult;
        if (opts.url === 'store/admin/affiliate/' && (opts.method === undefined || opts.method === 'GET')) {
            return mockListResult;
        }
        return { status: 200, data: { data: {} } };
    },
}));

jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

import ManageAffiliateProducts from './ManageAffiliateProducts';

beforeEach(() => {
    mockCalls.length = 0;
    mockSearchResult = {
        status: 200,
        data: { data: { candidates: [candidate], categories: [], listing_product_count: 1, fetch_failures: 0 } },
    };
    mockBulkAddResult = { status: 200, data: { data: { created: [5], skipped: [], total: 1 } } };
    // The list endpoint returns {products, categories} — categories ride
    // along so the picker can offer a dropdown even when a browse would fail.
    mockListResult = {
        status: 200,
        data: {
            data: {
                products: [affiliateProduct],
                categories: [{ path: 'product/category/2355/beauty-health', label: 'Beauty & Health' }],
            },
        },
    };
});

test('searching Rokomari shows a candidate with its price', async () => {
    render(<ManageAffiliateProducts />);
    fireEvent.change(screen.getByLabelText('Search Rokomari'), { target: { value: 'perfume' } });
    fireEvent.click(screen.getByText('Search'));

    await waitFor(() => expect(screen.getByText('Perfume A')).toBeInTheDocument());
    const searchCall = mockCalls.find((c) => c.url === 'store/admin/affiliate/search/');
    expect(searchCall.params.q).toBe('perfume');
});

test('selecting a candidate and adding posts it with the chosen link type', async () => {
    render(<ManageAffiliateProducts />);
    fireEvent.change(screen.getByLabelText('Search Rokomari'), { target: { value: 'perfume' } });
    fireEvent.click(screen.getByText('Search'));
    await waitFor(() => expect(screen.getByText('Perfume A')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Perfume A').closest('.MuiCard-root'));
    fireEvent.click(screen.getByText(/Add 1 selected/));

    await waitFor(() => expect(mockCalls.some((c) => c.url === 'store/admin/affiliate/bulk-add/')).toBe(true));
    const bulkCall = mockCalls.find((c) => c.url === 'store/admin/affiliate/bulk-add/');
    expect(bulkCall.body.candidates).toHaveLength(1);
    expect(bulkCall.body.candidates[0].remote_product_id).toBe('531074');
    expect(bulkCall.body.candidates[0].link_type).toBe('CART');
});

test('manage tab lists existing affiliate products with placement chips and click count', async () => {
    render(<ManageAffiliateProducts />);
    fireEvent.click(screen.getByText('Manage'));

    await waitFor(() => expect(screen.getByText('Perfume A')).toBeInTheDocument());
    expect(screen.getByText('Sidebar')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // click_count
});

test('editing a product opens the dialog with its manual_short_link field', async () => {
    render(<ManageAffiliateProducts />);
    fireEvent.click(screen.getByText('Manage'));
    await waitFor(() => expect(screen.getByText('Perfume A')).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText('Edit'));
    expect(await screen.findByText('Edit Affiliate Product')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Perfume A')).toBeInTheDocument();
});
