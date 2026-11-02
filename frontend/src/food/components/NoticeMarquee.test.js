import { render, screen } from '@testing-library/react';
import { noticeLines } from './NoticeMarquee';

let mockLang = 'en';
jest.mock('../context/FoodLocationContext', () => ({
  useFoodLocation: () => ({ lang: mockLang }),
}));

import NoticeMarquee from './NoticeMarquee';

beforeEach(() => { mockLang = 'en'; });

test('both notices appear in both languages, whatever the toggle says', () => {
  // These are disclosures, not chrome: a customer who never touched the
  // language toggle still has to be able to read them.
  for (const lang of ['en', 'bn']) {
    const lines = noticeLines(lang).join(' ');
    expect(lines).toMatch(/Prices of some items may vary/);
    expect(lines).toMatch(/কিছু খাবারের দাম পরিবর্তনশীল/);
    expect(lines).toMatch(/under construction/);
    expect(lines).toMatch(/মোবাইল অ্যাপ খুব শীঘ্রই আসছে/);
  }
});

test('the active language leads', () => {
  expect(noticeLines('bn')[0]).toMatch(/কিছু খাবারের দাম/);
  expect(noticeLines('en')[0]).toMatch(/Prices of some items/);
});

test('renders a duplicated track, but announces the text only once', () => {
  render(<NoticeMarquee />);
  const strip = screen.getByRole('status');
  // Two copies is what makes the scroll loop seamless; the second is
  // aria-hidden so a screen reader does not read the notices twice.
  const copies = strip.querySelectorAll('.notice-copy');
  expect(copies).toHaveLength(2);
  expect(copies[1]).toHaveAttribute('aria-hidden', 'true');
});
