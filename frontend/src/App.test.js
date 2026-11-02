import { render } from '@testing-library/react';
import { Provider } from 'react-redux';
import store from './redux/store/store';
import App from './App';

test('renders the app shell without crashing', () => {
  const { container } = render(
    <Provider store={store}>
      <App />
    </Provider>
  );
  expect(container.firstChild).not.toBeNull();
});
