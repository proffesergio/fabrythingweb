import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import PortalHeader from './PortalHeader';
import { fetchBreaking, fetchNewsCategories } from '../api';

jest.mock('../api', () => ({ ...jest.requireActual('../api'), fetchBreaking: jest.fn(), fetchNewsCategories: jest.fn() }));

function Location() {
  const location = useLocation();
  return <output aria-label="location">{location.pathname}{location.search}</output>;
}
function mount(path = '/nobleseek') {
  return render(<MemoryRouter initialEntries={[path]}><PortalHeader /><Location /></MemoryRouter>);
}
beforeEach(() => {
  fetchBreaking.mockResolvedValue([]);
  fetchNewsCategories.mockResolvedValue([]);
});

test('search edits the current query, trims submission, and closes the form', async () => {
  mount('/nobleseek?search=current');
  fireEvent.click(screen.getByRole('button', { name: 'খুঁজুন' }));
  const input = screen.getByRole('textbox', { name: 'খবর খুঁজুন' });
  expect(input).toHaveValue('current');
  fireEvent.change(input, { target: { value: '  new & query  ' } });
  fireEvent.submit(screen.getByRole('search'));
  await waitFor(() => expect(screen.getByLabelText('location')).toHaveTextContent('/nobleseek?search=new%20%26%20query'));
  expect(screen.queryByRole('search')).not.toBeInTheDocument();
});

test('Escape and close return keyboard focus to the search toggle', async () => {
  mount();
  const toggle = screen.getByRole('button', { name: 'খুঁজুন' });
  fireEvent.click(toggle);
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' });
  expect(screen.queryByRole('search')).not.toBeInTheDocument();
  expect(toggle).toHaveFocus();
  fireEvent.click(toggle);
  fireEvent.click(screen.getByRole('button', { name: 'বন্ধ' }));
  expect(toggle).toHaveFocus();
  await waitFor(() => expect(fetchNewsCategories).toHaveBeenCalled());
});

test('ticker exposes each story once to assistive technology and can pause', async () => {
  fetchBreaking.mockResolvedValue([{ id: 1, slug: 'breaking-story', headline: 'Breaking headline' }]);
  const { container } = mount();
  expect(await screen.findAllByRole('link', { name: /Breaking headline/ })).toHaveLength(1);
  const links = container.querySelectorAll('a[href="/nobleseek/breaking-story"]');
  expect(links).toHaveLength(2);
  expect(links[1]).toHaveAttribute('aria-hidden', 'true');
  expect(links[1]).toHaveAttribute('tabindex', '-1');
  fireEvent.click(screen.getByRole('button', { name: 'ব্রেকিং সংবাদ থামান' }));
  expect(container.querySelector('.ns-ticker-track')).toHaveStyle({ animationPlayState: 'paused' });
  fireEvent.click(screen.getByRole('button', { name: 'ব্রেকিং সংবাদ চালু করুন' }));
  expect(screen.getByRole('button', { name: 'ব্রেকিং সংবাদ থামান' })).toBeInTheDocument();
});

test('drawer category links close the drawer and navigate to the category', async () => {
  fetchNewsCategories.mockResolvedValue([{ slug: 'sports', name: 'খেলা' }]);
  mount();
  await screen.findByRole('link', { name: 'খেলা' });
  fireEvent.click(screen.getByRole('button', { name: 'সব বিভাগ' }));
  fireEvent.click(screen.getByRole('link', { name: 'খেলা' }));
  await waitFor(() => expect(screen.getByLabelText('location')).toHaveTextContent('/nobleseek?category=sports'));
  expect(screen.getByRole('button', { name: 'সব বিভাগ' })).toHaveAttribute('aria-expanded', 'false');
});
