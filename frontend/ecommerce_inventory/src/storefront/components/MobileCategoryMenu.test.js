import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MobileCategoryMenu } from './MegaMenu';

// Shape of GET /api/store/categories/ — a tree, not a flat list. The drawer
// used to render only the top level, so on a phone every subcategory was
// unreachable while the desktop mega menu listed them all.
const CATEGORIES = [
  {
    id: 29, slug: 'computers', name: 'Computers',
    children: [
      { id: 30, slug: 'computers-laptops', name: 'Laptops' },
      { id: 31, slug: 'computers-monitors', name: 'Monitors' },
    ],
  },
  {
    id: 61, slug: 'health', name: 'Health & Pharmacy',
    children: [
      { id: 62, slug: 'health-medicine', name: 'Medicine' },
      { id: 64, slug: 'health-supplement', name: 'Supplements' },
    ],
  },
  { id: 5, slug: 'eyewear', name: 'Eyewear', children: [] },
];

const renderMenu = (onClose = jest.fn()) =>
  render(<MemoryRouter><MobileCategoryMenu categories={CATEGORIES} onClose={onClose} /></MemoryRouter>);

test('lists every top-level category', () => {
  renderMenu();
  expect(screen.getByText('Computers')).toBeInTheDocument();
  expect(screen.getByText('Health & Pharmacy')).toBeInTheDocument();
  expect(screen.getByText('Eyewear')).toBeInTheDocument();
});

test('subcategories are reachable once expanded', () => {
  renderMenu();
  fireEvent.click(screen.getByLabelText('Expand Computers'));
  expect(screen.getByText('Laptops')).toBeInTheDocument();
  expect(screen.getByText('Monitors')).toBeInTheDocument();
});

test('expanding one parent does not expand the others', () => {
  renderMenu();
  fireEvent.click(screen.getByLabelText('Expand Health & Pharmacy'));
  expect(screen.getByText('Medicine')).toBeInTheDocument();
  // Collapse keeps children unmounted, so a computers child must be absent.
  expect(screen.queryByText('Laptops')).not.toBeInTheDocument();
});

test('a category with no children offers no expander', () => {
  renderMenu();
  expect(screen.queryByLabelText('Expand Eyewear')).not.toBeInTheDocument();
});

test('the parent row still links to its own listing', () => {
  renderMenu();
  expect(screen.getByText('Computers').closest('a')).toHaveAttribute('href', '/shop?category=computers');
});

test('a subcategory links to its own listing and closes the drawer', () => {
  const onClose = jest.fn();
  renderMenu(onClose);
  fireEvent.click(screen.getByLabelText('Expand Computers'));
  const laptops = screen.getByText('Laptops').closest('a');
  expect(laptops).toHaveAttribute('href', '/shop?category=computers-laptops');
  fireEvent.click(laptops);
  expect(onClose).toHaveBeenCalled();
});

test('tapping the expander does not navigate away', () => {
  const onClose = jest.fn();
  renderMenu(onClose);
  fireEvent.click(screen.getByLabelText('Expand Computers'));
  // onClose is the drawer-dismiss callback wired to navigation; expanding
  // must not trigger it or the menu would shut as you browse it.
  expect(onClose).not.toHaveBeenCalled();
});
