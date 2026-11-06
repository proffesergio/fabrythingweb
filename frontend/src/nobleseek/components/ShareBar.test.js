import React, { useEffect } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import ShareBar, { FacebookComments } from './ShareBar';

const canonicalUrl = 'https://nobleseek.fabrything.com/nobleseek/বাংলা-খবর';
const title = 'বাংলা খবর & updates';
const shareText = `${title} — নোবেলসিক`;
const clipboardDescriptor = Object.getOwnPropertyDescriptor(navigator, 'clipboard');

function setCanonical(href) {
  const link = document.createElement('link');
  link.rel = 'canonical';
  link.href = href;
  document.head.appendChild(link);
}

beforeEach(() => {
  window.history.replaceState({}, '', '/nobleseek/current?utm_source=facebook&amp=1#comments');
});

afterEach(() => {
  document.querySelectorAll('link[rel="canonical"]').forEach(link => link.remove());
  window.history.replaceState({}, '', '/');
  if (clipboardDescriptor) Object.defineProperty(navigator, 'clipboard', clipboardDescriptor);
  else delete navigator.clipboard;
});

test('uses accessible names and encodes the clean canonical URL for Facebook, X and WhatsApp', () => {
  setCanonical(`${canonicalUrl}?utm_campaign=test#comments`);
  render(<ShareBar title={title} />);
  const cleanUrl = new URL(canonicalUrl).href;
  const facebook = screen.getByRole('link', { name: 'Share on Facebook' });
  expect(facebook).toHaveAttribute('href', `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(cleanUrl)}`);
  expect(facebook).toHaveAttribute('target', '_blank');
  expect(facebook).toHaveAttribute('rel', 'noopener noreferrer');
  expect(screen.getByRole('link', { name: 'Share on X' })).toHaveAttribute(
    'href', `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(cleanUrl)}`,
  );
  expect(screen.getByRole('link', { name: 'Share on WhatsApp' })).toHaveAttribute(
    'href', `https://wa.me/?text=${encodeURIComponent(`${shareText} ${cleanUrl}`)}`,
  );
  expect(screen.getByRole('button', { name: 'Copy link' })).toBeInTheDocument();
});

test('prefers an explicit URL over canonical metadata and updates it when the prop changes', () => {
  setCanonical(canonicalUrl);
  const { rerender } = render(<ShareBar url="https://example.com/article?utm_source=test#share" />);
  expect(new URL(screen.getByRole('link', { name: 'Share on Facebook' }).href).searchParams.get('u'))
    .toBe('https://example.com/article');
  rerender(<ShareBar url="https://example.com/next?amp=1" vertical />);
  expect(new URL(screen.getByRole('link', { name: 'Share on Facebook' }).href).searchParams.get('u'))
    .toBe('https://example.com/next');
});

test('falls back to the clean current page path when canonical metadata is unavailable', () => {
  render(<ShareBar title={title} />);
  expect(new URL(screen.getByRole('link', { name: 'Share on Facebook' }).href).searchParams.get('u'))
    .toBe(`${window.location.origin}/nobleseek/current`);
});

test('reads canonical metadata published by a sibling SEO effect', () => {
  function Seo() {
    useEffect(() => { setCanonical(canonicalUrl); }, []);
    return null;
  }
  render(<><Seo /><ShareBar title={title} /></>);
  expect(new URL(screen.getByRole('link', { name: 'Share on Facebook' }).href).searchParams.get('u'))
    .toBe(new URL(canonicalUrl).href);
});

test('reports copy success only after the clipboard resolves and copies the clean canonical URL', async () => {
  setCanonical(`${canonicalUrl}?utm_source=test#share`);
  let finishCopy;
  const writeText = jest.fn().mockImplementation(() => new Promise(resolve => { finishCopy = resolve; }));
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  render(<ShareBar title={title} />);
  fireEvent.click(screen.getByRole('button', { name: 'Copy link' }));
  expect(writeText).toHaveBeenCalledWith(new URL(canonicalUrl).href);
  expect(screen.queryByText('Link copied')).not.toBeInTheDocument();
  finishCopy();
  expect(await screen.findByText('Link copied')).toBeInTheDocument();
});

test.each(['rejected', 'unavailable'])('reports failure when the clipboard is %s', async (state) => {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: state === 'rejected' ? { writeText: jest.fn().mockRejectedValue(new Error('Permission denied')) } : undefined,
  });
  render(<ShareBar title={title} />);
  fireEvent.click(screen.getByRole('button', { name: 'Copy link' }));
  expect(await screen.findByText('Could not copy link. Please try again.')).toBeInTheDocument();
  expect(screen.queryByText('Link copied')).not.toBeInTheDocument();
});

test('preserves the Facebook comments widget without developer setup text', () => {
  const { container } = render(<FacebookComments href={canonicalUrl} />);
  expect(container.querySelector('.fb-comments')).toHaveAttribute('data-href', canonicalUrl);
  expect(screen.queryByText(/Facebook SDK|FB App ID|index.html/)).not.toBeInTheDocument();
});
