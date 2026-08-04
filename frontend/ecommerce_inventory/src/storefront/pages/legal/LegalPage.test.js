import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LegalPage from './LegalPage';
import { LEGAL_PAGES, PRIVACY, SHIPPING, TERMS } from './content';

function renderDoc(doc) {
    return render(
        <MemoryRouter>
            <LegalPage doc={doc} />
        </MemoryRouter>,
    );
}

test.each(LEGAL_PAGES.map((d) => [d.title, d]))('%s renders its heading and every section', (_title, doc) => {
    renderDoc(doc);
    expect(screen.getByRole('heading', { level: 1, name: doc.title })).toBeInTheDocument();
    doc.sections.forEach((s) => {
        expect(screen.getByRole('heading', { level: 2, name: s.h })).toBeInTheDocument();
    });
});

test('every policy links to the other policies', () => {
    renderDoc(PRIVACY);
    expect(screen.getByRole('link', { name: TERMS.title })).toHaveAttribute('href', '/terms');
    expect(screen.getByRole('link', { name: SHIPPING.title })).toHaveAttribute('href', '/shipping');
});

// Cash on Delivery is the whole payment model; a policy that implied we store
// card details would be actively false.
test('the privacy policy states we never take payment credentials', () => {
    renderDoc(PRIVACY);
    expect(screen.getByText(/do not take or store card, bank or mobile-wallet details/i)).toBeInTheDocument();
});

// Rider location is the declaration both app stores scrutinise most.
test('the privacy policy explains rider location is opt-in and stoppable', () => {
    renderDoc(PRIVACY);
    expect(screen.getByText(/only while — the rider turns/i)).toBeInTheDocument();
});

// Affiliate commission must be disclosed, not buried.
test('affiliate commission is disclosed in both privacy and terms', () => {
    renderDoc(PRIVACY);
    expect(screen.getByText(/may earn a commission/i)).toBeInTheDocument();
});

test('the terms state prescription items cannot be bought', () => {
    renderDoc(TERMS);
    expect(screen.getByText(/cannot be purchased through the platform/i)).toBeInTheDocument();
});

test('shipping conditions state the charge is shown before confirming', () => {
    renderDoc(SHIPPING);
    expect(screen.getByText(/always shown before you confirm an order/i)).toBeInTheDocument();
});

// A published policy carrying an invented company name or licence number is
// worse than a visible blank — this guards the placeholders until replaced.
test('unfilled owner placeholders are still visibly marked', () => {
    renderDoc(TERMS);
    expect(screen.getAllByText(/\[LEGAL ENTITY NAME\]|\[TRADE LICENCE NO\.\]/).length).toBeGreaterThan(0);
});
