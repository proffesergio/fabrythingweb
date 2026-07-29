import { render, screen, waitFor, fireEvent } from '@testing-library/react';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));

const mockCalls = [];
let mockBrowseResult = null;
let mockImportResult = null;

const categoryTree = [
    { id: 3, slug: 'phones-smartphones', name: 'Smartphones', children: [] },
];

const candidates = [
    { source_url: 'https://potakait.com/phone-a', name: 'Phone A', price: 25000, discount_price: null, images: [], already_have: true },
    { source_url: 'https://potakait.com/phone-b', name: 'Phone B', price: 30000, discount_price: 28000, images: [], already_have: false },
];

jest.mock('../../hooks/APIHandler', () => () => ({
    loading: false,
    error: '',
    callApi: async (opts) => {
        mockCalls.push(opts);
        if (opts.url === 'products/categories/') {
            return { status: 200, data: { data: { data: categoryTree } } };
        }
        if (opts.url === 'products/admin/import/browse/') {
            return mockBrowseResult;
        }
        if (opts.url === 'products/admin/import/') {
            return mockImportResult;
        }
        return { status: 200, data: { data: {} } };
    },
}));

import ImportProducts from './ImportProducts';

beforeEach(() => {
    mockCalls.length = 0;
    mockBrowseResult = { status: 200, data: { data: { candidates, categories: [], listing_product_count: 2, fetch_failures: 0 } } };
    mockImportResult = null;
});

// Source defaults to potakait, which has no working search (verified live:
// every plausible search URL 404s) -- switch to a source that does before
// exercising the search-term flow.
const selectSource = (label) => {
    fireEvent.mouseDown(screen.getByLabelText('Source'));
    fireEvent.click(screen.getByRole('option', { name: label }));
};

test('potakait has no search box -- browsing is by category only', async () => {
    render(<ImportProducts />);

    expect(screen.queryByPlaceholderText('e.g. hoodie')).not.toBeInTheDocument();
    expect(screen.getByText(/Not available for this source/)).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByLabelText('Category on site'));
    fireEvent.click(await screen.findByRole('option', { name: 'Laptops' }));
    fireEvent.click(screen.getByText('Fetch latest'));

    await waitFor(() => expect(screen.getByText('Phone A')).toBeInTheDocument());
    const browseCall = mockCalls.find((c) => c.url === 'products/admin/import/browse/');
    expect(browseCall.params.source).toBe('potakait');
    expect(browseCall.params.category).toBe('laptops');
    expect(browseCall.params.q).toBeUndefined();
});

test('browsing canvasit by search term shows candidates with the already-have marker', async () => {
    render(<ImportProducts />);
    selectSource('Canvasit.com.bd');

    fireEvent.change(screen.getByPlaceholderText('e.g. hoodie'), { target: { value: 'phone' } });
    fireEvent.click(screen.getByText('Fetch latest'));

    await waitFor(() => expect(screen.getByText('Phone A')).toBeInTheDocument());
    expect(screen.getByText('Phone B')).toBeInTheDocument();
    expect(screen.getByText('Already in store')).toBeInTheDocument();

    const browseCall = mockCalls.find((c) => c.url === 'products/admin/import/browse/');
    expect(browseCall.params.source).toBe('canvasit');
    expect(browseCall.params.q).toBe('phone');
    expect(browseCall.rawError).toBe(true);
});

test('selecting a candidate and importing posts the picked URLs and target category, then shows results', async () => {
    render(<ImportProducts />);
    selectSource('Canvasit.com.bd');

    fireEvent.change(screen.getByPlaceholderText('e.g. hoodie'), { target: { value: 'phone' } });
    fireEvent.click(screen.getByText('Fetch latest'));
    await waitFor(() => expect(screen.getByText('Phone B')).toBeInTheDocument());

    // Select the not-yet-owned candidate (Phone B) via its card checkbox --
    // there are two checkboxes (one per candidate); pick the second.
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[1]);

    fireEvent.mouseDown(screen.getByLabelText('Import into category'));
    fireEvent.click(await screen.findByRole('option', { name: 'Smartphones' }));

    mockImportResult = {
        status: 200,
        data: {
            data: {
                results: [
                    { source_url: 'https://potakait.com/phone-b', status: 'imported', reason: null, product_id: 9, name: 'Phone B' },
                ],
                imported: 1, total: 1,
            },
        },
    };

    fireEvent.click(screen.getByText(/Import 1 selected/));

    await waitFor(() => expect(screen.getByText('Import results')).toBeInTheDocument());
    expect(screen.getByText('Imported')).toBeInTheDocument();
    // "Phone B" now appears twice: once in the candidate grid (still shown
    // above), once in the results row.
    expect(screen.getAllByText('Phone B').length).toBeGreaterThanOrEqual(2);

    const importCall = mockCalls.find((c) => c.url === 'products/admin/import/');
    expect(importCall.rawError).toBe(true);
    expect(importCall.body).toEqual({
        source: 'canvasit',
        source_urls: ['https://potakait.com/phone-b'],
        category_id: 3,
    });
});

test('a failed browse (rawError null-safe) surfaces the server message instead of a silent empty state', async () => {
    mockBrowseResult = { status: 502, data: { message: 'Could not fetch that listing', errors: ['boom'] } };
    render(<ImportProducts />);
    selectSource('Canvasit.com.bd');

    fireEvent.change(screen.getByPlaceholderText('e.g. hoodie'), { target: { value: 'phone' } });
    fireEvent.click(screen.getByText('Fetch latest'));

    await waitFor(() => expect(screen.getByText('Could not fetch that listing')).toBeInTheDocument());
});

test('a rejected search (field_errors.q) surfaces the field-specific message', async () => {
    mockBrowseResult = {
        status: 400,
        data: { message: 'Validation error', errors: ['nope'], field_errors: { q: ["canvasit search isn't available -- browse by category instead."] } },
    };
    render(<ImportProducts />);
    selectSource('Canvasit.com.bd');

    fireEvent.change(screen.getByPlaceholderText('e.g. hoodie'), { target: { value: 'phone' } });
    fireEvent.click(screen.getByText('Fetch latest'));

    await waitFor(() => expect(screen.getByText(/isn't available -- browse by category instead/)).toBeInTheDocument());
});

test('a failed import shows the per-product failure reason, not a fake success', async () => {
    render(<ImportProducts />);
    selectSource('Canvasit.com.bd');

    fireEvent.change(screen.getByPlaceholderText('e.g. hoodie'), { target: { value: 'phone' } });
    fireEvent.click(screen.getByText('Fetch latest'));
    await waitFor(() => expect(screen.getByText('Phone B')).toBeInTheDocument());

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.mouseDown(screen.getByLabelText('Import into category'));
    fireEvent.click(await screen.findByRole('option', { name: 'Smartphones' }));

    mockImportResult = { status: 400, data: { message: 'Validation error', errors: ['bad'], field_errors: {} } };
    fireEvent.click(screen.getByText(/Import 1 selected/));

    await waitFor(() => expect(screen.getByText('Import results')).toBeInTheDocument());
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Validation error')).toBeInTheDocument();
});

test('zero candidates with product links found but all unreadable is distinguished from a genuinely empty category', async () => {
    mockBrowseResult = {
        status: 200,
        data: { data: { candidates: [], categories: [], listing_product_count: 5, fetch_failures: 5 } },
    };
    render(<ImportProducts />);

    fireEvent.mouseDown(screen.getByLabelText('Category on site'));
    fireEvent.click(await screen.findByRole('option', { name: 'Laptops' }));
    fireEvent.click(screen.getByText('Fetch latest'));

    await waitFor(() => expect(screen.getByText(/couldn.t (fetch|read)/i)).toBeInTheDocument());
    expect(screen.queryByText('No products found for that category/search.')).not.toBeInTheDocument();
});

test('a genuinely empty category shows the plain "no products found" message', async () => {
    mockBrowseResult = {
        status: 200,
        data: { data: { candidates: [], categories: [], listing_product_count: 0, fetch_failures: 0 } },
    };
    render(<ImportProducts />);

    fireEvent.mouseDown(screen.getByLabelText('Category on site'));
    fireEvent.click(await screen.findByRole('option', { name: 'Laptops' }));
    fireEvent.click(screen.getByText('Fetch latest'));

    await waitFor(() => expect(screen.getByText('No products found for that category/search.')).toBeInTheDocument());
});
