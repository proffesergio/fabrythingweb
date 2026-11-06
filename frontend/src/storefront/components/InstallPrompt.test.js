import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter } from 'react-router-dom';
import InstallPrompt from './InstallPrompt';
import { INSTALL_DELAY_MS, needsManualIosInstructions } from '../../utils/pwa';

jest.mock('../../utils/pwa', () => ({
    ...jest.requireActual('../../utils/pwa'),
    needsManualIosInstructions: jest.fn(),
}));

beforeEach(() => {
    jest.useFakeTimers();
    localStorage.clear();
    needsManualIosInstructions.mockReturnValue(true);
});
afterEach(() => {
    act(() => jest.runOnlyPendingTimers());
    jest.useRealTimers();
    jest.restoreAllMocks();
});
function mount(path) {
    const router = createMemoryRouter([{ path: '*', element: <div /> }], { initialEntries: [path] });
    const view = render(<InstallPrompt router={router} />);
    act(() => jest.advanceTimersByTime(INSTALL_DELAY_MS));
    return { router, ...view };
}

test.each(['/nobleseek', '/nobleseek/', '/nobleseek/story', '/nobleseek/about'])('does not offer the shopping install prompt on %s', (path) => {
    mount(path);
    expect(screen.queryByText('Install Fabrything')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Add to Home Screen' })).not.toBeInTheDocument();
});

test('storefront keeps its delayed install prompt and iOS instructions', () => {
    const router = createMemoryRouter([{ path: '*', element: <div /> }], { initialEntries: ['/shop'] });
    render(<InstallPrompt router={router} />);
    expect(screen.queryByText('Install Fabrything')).not.toBeInTheDocument();
    act(() => jest.advanceTimersByTime(INSTALL_DELAY_MS));
    expect(screen.getByText('Install Fabrything')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Install' }));
    expect(screen.getByRole('heading', { name: 'Add to Home Screen' })).toBeInTheDocument();
});

test('SPA navigation immediately hides the banner and any open install instructions on news', async () => {
    const { router } = mount('/shop');
    fireEvent.click(screen.getByRole('button', { name: 'Install' }));
    expect(screen.getByRole('heading', { name: 'Add to Home Screen' })).toBeInTheDocument();
    await act(async () => router.navigate('/nobleseek/story'));
    expect(screen.queryByText('Install Fabrything')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Add to Home Screen' })).not.toBeInTheDocument();
});

test('the prompt remains available when navigating from news to the shop', async () => {
    const { router } = mount('/nobleseek');
    await act(async () => router.navigate('/shop'));
    expect(screen.getByText('Install Fabrything')).toBeInTheDocument();
});

test('the dedicated news hostname suppresses the shop prompt even at its root', () => {
    jest.spyOn(window, 'location', 'get').mockReturnValue({ ...window.location, hostname: 'nobleseek.fabrything.com' });
    mount('/');
    expect(screen.queryByText('Install Fabrything')).not.toBeInTheDocument();
});
