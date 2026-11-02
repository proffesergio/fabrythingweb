import { articleShareUrl, nativeShareOrCopy, shareLinks } from './share';
import { getPollSession } from './api';

describe('share links', () => {
  test('article URL carries the slug on the current origin', () => {
    expect(articleShareUrl('my-story')).toBe(`${window.location.origin}/nobleseek/my-story`);
  });
  test('all four networks embed the article URL', () => {
    const links = shareLinks('https://fabrything.com/nobleseek/x', 'শিরোনাম');
    const enc = encodeURIComponent('https://fabrything.com/nobleseek/x');
    expect(links.facebook).toContain(enc);
    expect(links.x).toContain(enc);
    expect(links.whatsapp).toContain(enc);
    expect(links.telegram).toContain(enc);
  });
  test('clipboard fallback copies when Web Share is missing', async () => {
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, 'clipboard', { value: { writeText }, configurable: true });
    const r = await nativeShareOrCopy({ title: 't', text: 't', url: 'https://x/y' });
    expect(r).toBe('copied');
    expect(writeText).toHaveBeenCalledWith('https://x/y');
  });
});

describe('poll session', () => {
  test('stable within a browser, unique across clears', () => {
    localStorage.clear();
    const a = getPollSession();
    const b = getPollSession();
    expect(a).toBe(b);
    expect(a.length).toBeGreaterThan(8);
  });
});
