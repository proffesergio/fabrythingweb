import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdSlot from './AdSlot';
import { loadAdSense, useAdConfig } from './adsConfig';
jest.mock('./adsConfig', () => ({
  ...jest.requireActual('./adsConfig'),
  useAdConfig: jest.fn(), loadAdSense: jest.fn(() => Promise.resolve(false)),
}));
beforeEach(() => { useAdConfig.mockReturnValue({}); loadAdSense.mockClear(); });
const at = (path, props = {}) => render(<MemoryRouter initialEntries={[path]}><AdSlot placement="sidebar" {...props} /></MemoryRouter>);
test('reserves a labelled responsive news placement without demo instructions or loading ads', () => {
  at('/nobleseek');
  const ad = screen.getByRole('complementary', { name: 'Advertisement' });
  expect(ad).toHaveStyle({ maxWidth: '300px', width: '100%' });
  expect(ad).toHaveTextContent('Advertisement');
  expect(screen.queryByText(/placeholder|set slot/i)).toBeNull();
  expect(loadAdSense).not.toHaveBeenCalled();
});
test('never shows reserved ads on storefront pages', () => {
  at('/product/test');
  expect(screen.queryByRole('complementary')).toBeNull();
});
test('blog permits a leaderboard up to 970 pixels wide', () => {
  at('/blog/article', { placement: 'leaderboard' });
  expect(screen.getByRole('complementary')).toHaveStyle({ maxWidth: '970px' });
});
