import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FoodComingSoon from './FoodComingSoon';

jest.mock('../../hooks/APIHandler', () => () => ({
    callApi: jest.fn().mockResolvedValue({ data: { data: { data: [], totalPages: 1, currentPage: 1, totalItems: 0 } } }),
    loading: false,
}));

test('renders the Food heading and an empty-state message when no restaurants are active yet', async () => {
    render(
        <MemoryRouter>
            <FoodComingSoon />
        </MemoryRouter>
    );

    expect(await screen.findByRole('heading', { level: 1, name: /Food/i })).toBeInTheDocument();
    expect(screen.getByText(/no restaurants have gone live/i)).toBeInTheDocument();
});
