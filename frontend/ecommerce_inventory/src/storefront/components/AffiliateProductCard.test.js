import { render, screen, fireEvent } from '@testing-library/react';
import AffiliateProductCard, { pingClick } from './AffiliateProductCard';

// Shape of GET /api/store/partner-picks/ in production (captured 2026-08-08).
const ITEM = {
  id: 1,
  program: 'rokomari',
  program_label: 'Rokomari',
  title: 'Dabo Whitening and Shining Rice Ferment Foam Face Wash 180ml',
  brand: 'Dabo',
  image: 'https://cdn/face-wash.jpg',
  original_price: '1400.00',
  current_price: '1069.00',
  go_url: 'https://fabrythingweb.onrender.com/api/store/partner-picks/1/r/',
  target_url: 'https://rkmri.co/3Eoeep05NRA5/',
};

const card = () => screen.getByRole('link');

describe('the whole card is the link', () => {
  it('links to the affiliate destination, not our own redirect host', () => {
    // Sending the shopper through go_url put fabrythingweb.onrender.com in
    // front of them, and a cold free-tier start left them on a blank Render
    // page for ~50s before the 302 fired.
    render(<AffiliateProductCard item={ITEM} />);
    expect(card()).toHaveAttribute('href', 'https://rkmri.co/3Eoeep05NRA5/');
  });

  it('opens in a new tab, safely', () => {
    render(<AffiliateProductCard item={ITEM} />);
    expect(card()).toHaveAttribute('target', '_blank');
    expect(card().getAttribute('rel')).toContain('noopener');
    expect(card().getAttribute('rel')).toContain('sponsored');
  });

  it('makes the image and title part of the link, not just a button', () => {
    // Only a "Shop Now" button used to be clickable, so tapping the photo or
    // the name — what people actually do — did nothing at all.
    render(<AffiliateProductCard item={ITEM} />);
    expect(card()).toContainElement(screen.getByRole('img'));
    expect(card()).toContainElement(screen.getByText(ITEM.title));
  });

  it('falls back to the tracked redirect when no target is resolvable', () => {
    render(<AffiliateProductCard item={{ ...ITEM, target_url: null }} />);
    expect(card()).toHaveAttribute('href', ITEM.go_url);
  });
});

describe('click tracking', () => {
  afterEach(() => { delete navigator.sendBeacon; });

  it('reports the click without delaying navigation', () => {
    const beacon = jest.fn();
    navigator.sendBeacon = beacon;
    render(<AffiliateProductCard item={ITEM} />);

    fireEvent.click(card());
    expect(beacon).toHaveBeenCalledWith(ITEM.go_url);
  });

  it('also reports a middle-click / open-in-new-tab', () => {
    const beacon = jest.fn();
    navigator.sendBeacon = beacon;
    render(<AffiliateProductCard item={ITEM} />);
    // This RTL build has no fireEvent.auxClick helper; dispatch the DOM event
    // React actually listens for.
    fireEvent(card(), new MouseEvent('auxclick', { bubbles: true, cancelable: true }));
    expect(beacon).toHaveBeenCalledWith(ITEM.go_url);
  });

  it('a blocked or throwing tracker never breaks the click', () => {
    // An ad blocker may kill the beacon. The customer's navigation must be
    // unaffected — tracking is best-effort, the click is not.
    navigator.sendBeacon = () => { throw new Error('blocked'); };
    expect(() => pingClick(ITEM.go_url)).not.toThrow();
  });

  it('does nothing when there is no tracking URL', () => {
    const beacon = jest.fn();
    navigator.sendBeacon = beacon;
    pingClick(undefined);
    expect(beacon).not.toHaveBeenCalled();
  });
});

describe('presentation', () => {
  it('badges the source so nobody is surprised to leave the site', () => {
    render(<AffiliateProductCard item={ITEM} />);
    expect(screen.getByText('via Rokomari')).toBeInTheDocument();
    expect(screen.getByText(/Buy on Rokomari/)).toBeInTheDocument();
  });

  it('shows the discount the way the store cards do', () => {
    render(<AffiliateProductCard item={ITEM} />);
    expect(screen.getByText('৳1069.00')).toBeInTheDocument();
    expect(screen.getByText('৳1400.00')).toBeInTheDocument();
    expect(screen.getByText('-24%')).toBeInTheDocument();
  });

  it('omits the discount chip when there is no saving', () => {
    render(<AffiliateProductCard item={{ ...ITEM, original_price: '1069.00' }} />);
    expect(screen.queryByText(/^-\d+%$/)).not.toBeInTheDocument();
  });

  it('renders nothing for a missing item rather than crashing', () => {
    const { container } = render(<AffiliateProductCard item={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
