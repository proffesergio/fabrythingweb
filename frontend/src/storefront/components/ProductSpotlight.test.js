import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProductSpotlight from './ProductSpotlight';

jest.mock('framer-motion', () => ({useReducedMotion: () => false}));
const products = [{slug: 'cotton-shirt', name: 'Cotton shirt', image: ['https://example.test/one.webp', 'https://example.test/two.webp']}];
const show = (props = {}) => render(<MemoryRouter><ProductSpotlight products={products} {...props} /></MemoryRouter>);

test('real product destination and safe image fallback remain usable', () => {
    show();
    expect(screen.getByRole('link', {name: 'View Cotton shirt'})).toHaveAttribute('href', '/product/cotton-shirt');
    fireEvent.error(screen.getByAltText('Cotton shirt'));
    expect(screen.getByAltText('Cotton shirt')).toHaveAttribute('src', 'https://example.test/two.webp');
    fireEvent.error(screen.getByAltText('Cotton shirt'));
    expect(screen.getByRole('link', {name: /Browse the catalog/})).toHaveAttribute('href', '/shop');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
});

test('motion can be paused without hiding product navigation', () => {
    show();
    fireEvent.click(screen.getByRole('button', {name: 'Pause banner animation'}));
    expect(screen.getByRole('region', {name: 'Everyday style. A fresh perspective.'})).toHaveClass('product-spotlight--paused');
    expect(screen.getByRole('link', {name: /View product/})).toHaveAttribute('href', '/product/cotton-shirt');
});

test('selects distinct catalog products and avoids invented product information', () => {
    show({products: [...products, ...products, {slug: 'headphones', name: 'Headphones', image: ['https://example.test/headphones.webp']}]});
    fireEvent.click(screen.getByRole('button', {name: 'Show Headphones'}));
    expect(screen.getByRole('link', {name: 'View Headphones'})).toHaveAttribute('href', '/product/headphones');
    expect(screen.queryByText(/New Release|% off|৳/)).not.toBeInTheDocument();
});
