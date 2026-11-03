import { FoodThemeProvider } from './context/FoodThemeContext';
import { FoodLocationProvider } from './context/FoodLocationContext';
import FoodLayout from './layout/FoodLayout';

// Keep the food shell, location picker and map out of the Shop's first load.
export default function FoodApp() {
  return <FoodThemeProvider><FoodLocationProvider><FoodLayout /></FoodLocationProvider></FoodThemeProvider>;
}
