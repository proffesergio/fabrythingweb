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

test('food layout renders the brand', () => {
  render(
    <Provider store={store}>
      <ThemeProvider theme={getFoodTheme()}>
        <MemoryRouter initialEntries={['/food']}>
          <Routes><Route path="/food" element={<FoodLayout />} /></Routes>
        </MemoryRouter>
      </ThemeProvider>
    </Provider>
  );
  expect(screen.getByText(/food/i)).toBeInTheDocument();
});
