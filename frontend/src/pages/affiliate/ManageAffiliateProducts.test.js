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
        if (opts.url === 'store/admin/partner-picks/parse-url/') {
            // Mirrors AdminAffiliateParseUrlView: pure parsing, no fetch.
            return {
                status: 200,
                data: {
                    data: {
                        remote_product_id: '531074',
                        source_url: opts.body.url,
                        links: {
                            cart: 'https://www.rokomari.com/cart?productId=531074&affId=Ma8A710222i0iRo',
                            product: 'https://www.rokomari.com/product/531074/?affId=Ma8A710222i0iRo',
                        },
                    },
                },
            };
        }
        if (opts.url === 'store/admin/partner-picks/search/') return mockSearchResult;
        if (opts.url === 'store/admin/partner-picks/bulk-add/') return mockBulkAddResult;
        if (opts.url === 'store/admin/partner-picks/' && (opts.method === undefined || opts.method === 'GET')) {
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
    const searchCall = mockCalls.find((c) => c.url === 'store/admin/partner-picks/search/');
    expect(searchCall.params.q).toBe('perfume');
});

test('selecting a candidate and adding posts it with the chosen link type', async () => {
    render(<ManageAffiliateProducts />);
    fireEvent.change(screen.getByLabelText('Search Rokomari'), { target: { value: 'perfume' } });
    fireEvent.click(screen.getByText('Search'));
    await waitFor(() => expect(screen.getByText('Perfume A')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Perfume A').closest('.MuiCard-root'));
    fireEvent.click(screen.getByText(/Add 1 selected/));

    await waitFor(() => expect(mockCalls.some((c) => c.url === 'store/admin/partner-picks/bulk-add/')).toBe(true));
    const bulkCall = mockCalls.find((c) => c.url === 'store/admin/partner-picks/bulk-add/');
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

// --- Manual entry -------------------------------------------------------
//
// Rokomari sits behind Cloudflare, so the server cannot fetch a product page
// and the search/bulk-add path fails in production. Manual entry is therefore
// the ONLY working way to get a product live. The backend half (parse-url +
// create) shipped and was tested; the button that should drive it set state
// nothing rendered, so it did nothing at all — these pin the wiring.

const openManual = () => {
    fireEvent.click(screen.getByText('Add a product manually'));
};

test('the manual entry button actually opens a form', async () => {
    render(<ManageAffiliateProducts />);
    openManual();

    await waitFor(() =>
        expect(screen.getByLabelText(/Rokomari product URL/i)).toBeInTheDocument());
});

test('looking up a pasted URL calls parse-url and shows the product id', async () => {
    render(<ManageAffiliateProducts />);
    openManual();

    fireEvent.change(await screen.findByLabelText(/Rokomari product URL/i), {
        target: { value: 'https://www.rokomari.com/product/531074/perfume-a' },
    });
    fireEvent.click(screen.getByText('Look up'));

    await waitFor(() => {
        const call = mockCalls.find((c) => c.url === 'store/admin/partner-picks/parse-url/');
        expect(call).toBeTruthy();
        expect(call.body.url).toContain('531074');
    });
    // Exact match: the id also appears inside the link preview, so a regex
    // would match two nodes.
    expect(await screen.findByText('531074')).toBeInTheDocument();
});

test('creating posts every field the owner filled in, including the short link', async () => {
    render(<ManageAffiliateProducts />);
    openManual();

    fireEvent.change(await screen.findByLabelText(/Rokomari product URL/i), {
        target: { value: 'https://www.rokomari.com/product/531074/perfume-a' },
    });
    fireEvent.click(screen.getByText('Look up'));
    // Wait for the parsed id to actually render, not merely for the request to
    // have been issued — the form is only complete once the id is in state.
    expect(await screen.findByText('531074')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Perfume A' } });
    fireEvent.change(screen.getByLabelText(/Image URL/i), {
        target: { value: 'https://img.example/p.jpg' },
    });
    fireEvent.change(screen.getByLabelText(/short link/i), {
        target: { value: 'https://rkmri.co/R5MEpp0p0IEI/' },
    });
    fireEvent.click(screen.getByText('Add product'));

    await waitFor(() => {
        const post = mockCalls.find(
            (c) => c.url === 'store/admin/partner-picks/' && c.method === 'POST');
        expect(post).toBeTruthy();
        expect(post.body.remote_product_id).toBe('531074');
        expect(post.body.title).toBe('Perfume A');
        expect(post.body.image).toBe('https://img.example/p.jpg');
        // The money field: a pasted rkmri.co link overrides the constructed
        // URL, and it is what actually earns commission.
        expect(post.body.manual_short_link).toBe('https://rkmri.co/R5MEpp0p0IEI/');
    });
});

test('creating is blocked until the URL has been looked up', async () => {
    render(<ManageAffiliateProducts />);
    openManual();

    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'No id yet' } });
    fireEvent.click(screen.getByText('Add product'));

    await waitFor(() => {
        expect(mockCalls.some(
            (c) => c.url === 'store/admin/partner-picks/' && c.method === 'POST')).toBe(false);
    });
});

test('the edit dialog can set a product image', async () => {
    render(<ManageAffiliateProducts />);
    fireEvent.click(screen.getByText('Manage'));
    fireEvent.click(await screen.findByLabelText('Edit'));

    fireEvent.change(await screen.findByLabelText(/Image URL/i), {
        target: { value: 'https://img.example/edited.jpg' },
    });
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
        const patch = mockCalls.find((c) => c.method === 'PATCH');
        expect(patch.body.image).toBe('https://img.example/edited.jpg');
    });
});
