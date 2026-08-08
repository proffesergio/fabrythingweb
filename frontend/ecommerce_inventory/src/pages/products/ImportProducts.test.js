import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';

// useParams drives the per-source routes (/manage/import/<slug>); with no
// param the picker is unlocked, which is what these tests exercise.
jest.mock('react-router-dom', () => ({
    useNavigate: () => jest.fn(),
    useParams: () => ({}),
}));

const mockCalls = [];
let mockBrowseResult = null;
let mockImportResult = null;
let mockRunsResult = null;
let mockSourcesResult = null;

const categoryTree = [
    { id: 3, slug: 'phones-smartphones', name: 'Smartphones', children: [] },
];

const candidates = [
    { source_url: 'https://potakait.com/phone-a', name: 'Phone A', price: 25000, discount_price: null, images: [], already_have: true },
    { source_url: 'https://potakait.com/phone-b', name: 'Phone B', price: 30000, discount_price: 28000, images: [], already_have: false },
];

// Mirrors the DB-seeded rows (catalog/migrations/0008_seed_import_sources.py)
// closely enough to exercise the picker/management/history views without
// depending on exact wording -- the source list is API-driven now, not a
// frontend constant, so these are just plausible server responses.
const potakait = {
    id: 1, name: 'Potakait.com', slug: 'potakait', base_url: 'https://potakait.com/',
    adapter_key: 'opencart', supports_search: false, is_enabled: true, sets_source_url: true,
    notes: '', last_synced_at: null,
    categories: [{ id: 101, source_path: 'laptops', label: 'Laptops', our_category_slug: 'computers-laptops', display_order: 0 }],
};
const canvasit = {
    id: 2, name: 'Canvasit.com.bd', slug: 'canvasit', base_url: 'https://canvasit.com.bd/',
    adapter_key: 'opencart', supports_search: true, is_enabled: true, sets_source_url: true,
    notes: '', last_synced_at: null,
    categories: [{ id: 201, source_path: 'laptop', label: 'Laptops', our_category_slug: 'computers-laptops', display_order: 0 }],
};
const fabrilife = {
    id: 3, name: 'Fabrilife.com', slug: 'fabrilife', base_url: 'https://fabrilife.com/',
    adapter_key: 'fabrilife', supports_search: true, is_enabled: true, sets_source_url: false,
    notes: '', last_synced_at: null, categories: [],
};
const arogga = {
    id: 4, name: 'Arogga.com', slug: 'arogga', base_url: 'https://www.arogga.com/',
    adapter_key: '', supports_search: false, is_enabled: false, sets_source_url: false,
    notes: 'No working adapter exists yet -- client-rendered, no reachable product API.',
    last_synced_at: null, categories: [],
};
const sourcesFixture = [potakait, canvasit, fabrilife, arogga];

jest.mock('../../hooks/APIHandler', () => () => ({
    loading: false,
    error: '',
    callApi: async (opts) => {
        mockCalls.push(opts);
        if (opts.url === 'products/categories/') {
            return { status: 200, data: { data: { data: categoryTree } } };
        }
        if (opts.url === 'products/admin/import/sources/' && opts.method === 'GET') {
            return mockSourcesResult;
        }
        if (opts.url === 'products/admin/import/sources/' && opts.method === 'POST') {
            return { status: 201, data: { data: { ...potakait, id: 99, name: opts.body.name, slug: opts.body.slug, categories: [] } } };
        }
        if (/products\/admin\/import\/sources\/\d+\/$/.test(opts.url) && opts.method === 'PATCH') {
            return { status: 200, data: { data: { ...potakait, ...opts.body } } };
        }
        if (/products\/admin\/import\/sources\/\d+\/categories\/$/.test(opts.url) && opts.method === 'POST') {
            return { status: 201, data: { data: { id: 555, ...opts.body } } };
        }
        if (opts.url === 'products/admin/import/browse/') {
            return mockBrowseResult;
        }
        if (opts.url === 'products/admin/import/') {
            return mockImportResult;
        }
        if (opts.url === 'products/admin/import/runs/') {
            return mockRunsResult;
        }
        return { status: 200, data: { data: {} } };
    },
}));

import ImportProducts from './ImportProducts';

beforeEach(() => {
    mockCalls.length = 0;
    mockBrowseResult = { status: 200, data: { data: { candidates, categories: [], listing_product_count: 2, fetch_failures: 0 } } };
    mockImportResult = null;
    mockRunsResult = { status: 200, data: { data: { data: [] } } };
    mockSourcesResult = { status: 200, data: { data: sourcesFixture } };
});

// Source defaults to the first enabled source in the API response (potakait,
// which has no working search -- verified live: every plausible search URL
// 404s) -- switch to a source that does before exercising the search-term
// flow.
const selectSource = (label) => {
    fireEvent.mouseDown(screen.getByLabelText('Source'));
    fireEvent.click(screen.getByRole('option', { name: label }));
};

// Sources load asynchronously now (GET products/admin/import/sources/)
// instead of coming from a hardcoded frontend list -- wait for the fetch to
// land and the default source to be selected before interacting with
// anything that depends on it.
const waitForSourcesLoaded = async () => {
    await waitFor(() => expect(screen.getByText('Fetch latest').closest('button')).not.toBeDisabled());
};

test('source picker is populated from the API, including a disabled arogga', async () => {
    render(<ImportProducts />);
    await waitForSourcesLoaded();

    fireEvent.mouseDown(screen.getByLabelText('Source'));
    expect(screen.getByRole('option', { name: 'Potakait.com' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Canvasit.com.bd' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Fabrilife.com' })).toBeInTheDocument();
    const aroggaOption = screen.getByRole('option', { name: /Arogga.com/ });
    expect(aroggaOption).toBeInTheDocument();
    expect(aroggaOption).toHaveAttribute('aria-disabled', 'true');
});

test('potakait has no search box -- browsing is by category only', async () => {
    render(<ImportProducts />);
    await waitForSourcesLoaded();

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
    await waitForSourcesLoaded();
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
    await waitForSourcesLoaded();
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
                imported: 1, total: 1, run_id: 42,
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
    await waitForSourcesLoaded();
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
    await waitForSourcesLoaded();
    selectSource('Canvasit.com.bd');

    fireEvent.change(screen.getByPlaceholderText('e.g. hoodie'), { target: { value: 'phone' } });
    fireEvent.click(screen.getByText('Fetch latest'));

    await waitFor(() => expect(screen.getByText(/isn't available -- browse by category instead/)).toBeInTheDocument());
});

test('a failed import shows the per-product failure reason, not a fake success', async () => {
    render(<ImportProducts />);
    await waitForSourcesLoaded();
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
    await waitForSourcesLoaded();

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
    await waitForSourcesLoaded();

    fireEvent.mouseDown(screen.getByLabelText('Category on site'));
    fireEvent.click(await screen.findByRole('option', { name: 'Laptops' }));
    fireEvent.click(screen.getByText('Fetch latest'));

    await waitFor(() => expect(screen.getByText('No products found for that category/search.')).toBeInTheDocument());
});

describe('Manage Sources tab', () => {
    test('lists sources with enable/disable switches and lets the admin toggle one', async () => {
        render(<ImportProducts />);
        await waitForSourcesLoaded();

        fireEvent.click(screen.getByText('Manage Sources'));
        await waitFor(() => expect(screen.getByText('Fabrilife.com')).toBeInTheDocument());

        // Arogga shows as Disabled with its reason.
        expect(screen.getByText('Disabled', { selector: 'span' })).toBeInTheDocument();
        expect(screen.getByText(/no reachable product API/)).toBeInTheDocument();

        // Flip potakait's switch off.
        const potakaitCard = screen.getByText('Potakait.com').closest('.MuiCard-root');
        const toggle = within(potakaitCard).getByRole('checkbox');
        fireEvent.click(toggle);

        await waitFor(() => {
            const patchCall = mockCalls.find((c) => c.url === 'products/admin/import/sources/1/' && c.method === 'PATCH');
            expect(patchCall).toBeTruthy();
            expect(patchCall.body).toEqual({ is_enabled: false });
        });
    });

    test('adding a new source posts the form and reloads the list', async () => {
        render(<ImportProducts />);
        await waitForSourcesLoaded();
        fireEvent.click(screen.getByText('Manage Sources'));
        await waitFor(() => expect(screen.getByText('Fabrilife.com')).toBeInTheDocument());

        fireEvent.click(screen.getByText('Add source'));
        const dialog = await screen.findByRole('dialog');
        fireEvent.change(within(dialog).getByLabelText('Name'), { target: { value: 'New Store' } });
        fireEvent.change(within(dialog).getByLabelText('Slug'), { target: { value: 'newstore' } });
        fireEvent.click(within(dialog).getByText('Save'));

        await waitFor(() => {
            const postCall = mockCalls.find((c) => c.url === 'products/admin/import/sources/' && c.method === 'POST');
            expect(postCall).toBeTruthy();
            expect(postCall.body.name).toBe('New Store');
            expect(postCall.body.slug).toBe('newstore');
        });
    });

    test('adding a category mapping to a source posts to that source\'s categories endpoint', async () => {
        render(<ImportProducts />);
        await waitForSourcesLoaded();
        fireEvent.click(screen.getByText('Manage Sources'));
        await waitFor(() => expect(screen.getByText('Fabrilife.com')).toBeInTheDocument());

        const fabrilifeCard = screen.getByText('Fabrilife.com').closest('.MuiCard-root');
        fireEvent.click(within(fabrilifeCard).getByText('Add mapping'));

        const dialog = await screen.findByRole('dialog');
        fireEvent.change(within(dialog).getByLabelText('Source path'), { target: { value: 'men-caps' } });
        fireEvent.change(within(dialog).getByLabelText('Label'), { target: { value: 'Caps' } });
        fireEvent.change(within(dialog).getByLabelText('Our category slug'), { target: { value: 'men-caps' } });
        fireEvent.click(within(dialog).getByText('Save'));

        await waitFor(() => {
            const postCall = mockCalls.find((c) => c.url === 'products/admin/import/sources/3/categories/' && c.method === 'POST');
            expect(postCall).toBeTruthy();
            expect(postCall.body).toEqual({ source_path: 'men-caps', label: 'Caps', our_category_slug: 'men-caps' });
        });
    });
});

describe('Sync History tab', () => {
    test('lists past import runs with their counts', async () => {
        mockRunsResult = {
            status: 200,
            data: {
                data: {
                    data: [
                        { id: 1, source_name: 'Potakait.com', source_slug: 'potakait', status: 'COMPLETED',
                          started_at: '2026-07-30T10:00:00Z', found_count: 3, imported_count: 2, skipped_count: 1,
                          failed_count: 0, triggered_by: 'root', error_summary: '' },
                    ],
                },
            },
        };
        render(<ImportProducts />);
        await waitForSourcesLoaded();
        fireEvent.click(screen.getByText('Sync History'));

        await waitFor(() => expect(screen.getByText('Potakait.com')).toBeInTheDocument());
        expect(screen.getByText('Completed')).toBeInTheDocument();
        expect(screen.getByText('root')).toBeInTheDocument();

        const runsCall = mockCalls.find((c) => c.url === 'products/admin/import/runs/');
        expect(runsCall).toBeTruthy();
    });

    test('filtering by source re-fetches with the source param', async () => {
        render(<ImportProducts />);
        await waitForSourcesLoaded();
        fireEvent.click(screen.getByText('Sync History'));
        await waitFor(() => expect(mockCalls.some((c) => c.url === 'products/admin/import/runs/')).toBe(true));

        mockCalls.length = 0;
        fireEvent.mouseDown(screen.getAllByLabelText('Source')[0]);
        fireEvent.click(screen.getByRole('option', { name: 'Fabrilife.com' }));

        await waitFor(() => {
            const runsCall = mockCalls.find((c) => c.url === 'products/admin/import/runs/');
            expect(runsCall).toBeTruthy();
            expect(runsCall.params.source).toBe('fabrilife');
        });
    });
});
