import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import foodCartReducer from '../redux/foodCartSlice';
import { getFoodTheme } from '../theme';
import FoodLayout from './FoodLayout';

// Minimal store — avoids importing the full app store (which pulls in axios ESM
// via the sidebar thunk and breaks CRA's Jest parser).
const store = configureStore({ reducer: { foodCart: foodCartReducer } });

const renderLayout = () =>
  render(
    <Provider store={store}>
      <ThemeProvider theme={getFoodTheme()}>
        <MemoryRouter initialEntries={['/food']}>
          <Routes><Route path="/food" element={<FoodLayout />} /></Routes>
        </MemoryRouter>
      </ThemeProvider>
    </Provider>
  );

test('food layout renders the Fabrything Food brand mark', () => {
  renderLayout();
  // The brand is an image now, not a text wordmark, so it is asserted through
  // its alt text — which is also what a screen reader announces.
  expect(screen.getByAltText('Fabrything Food')).toBeInTheDocument();
});

test('the food brand mark is the food logo, never the store one', () => {
  // The two brands must not leak into each other's surfaces. Pinning the asset
  // catches a wrong `brand` prop, which otherwise looks fine until someone
  // notices the store logo sitting on the food header.
  renderLayout();
  expect(screen.getByAltText('Fabrything Food'))
    .toHaveAttribute('src', expect.stringContaining('/food-horizontal'));
  expect(screen.queryByAltText('Fabrything')).not.toBeInTheDocument();
});
