import { getToken, isSignedIn, isExpired, clearToken, isTokenRejection } from './authToken';

// Minimal unsigned JWT — only the payload matters here; nothing in the app
// verifies the signature client-side.
const jwt = (payload) =>
  `${btoa('{"alg":"HS256"}')}.${btoa(JSON.stringify(payload))}.sig`;

const inHours = (h) => Math.floor(Date.now() / 1000) + h * 3600;

beforeEach(() => localStorage.clear());

describe('getToken', () => {
  test('returns a live token', () => {
    localStorage.setItem('token', jwt({ exp: inHours(1) }));
    expect(getToken()).toBeTruthy();
    expect(isSignedIn()).toBe(true);
  });

  test('an expired token is withheld AND purged', () => {
    // The whole point: a dead token left in storage kept being attached to
    // every request, so the server 401'd calls that welcome anonymous callers
    // — including a guest placing an order.
    localStorage.setItem('token', jwt({ exp: inHours(-1) }));
    expect(getToken()).toBe('');
    expect(localStorage.getItem('token')).toBeNull();
    expect(isSignedIn()).toBe(false);
  });

  test('no token at all is not an error', () => {
    expect(getToken()).toBe('');
    expect(isSignedIn()).toBe(false);
  });

  test('a malformed value is treated as no token, not as a live one', () => {
    localStorage.setItem('token', 'not-a-jwt');
    // Undecodable, so we cannot prove it is dead — it is still sent, and the
    // server's 401 path clears it. What must not happen is a crash.
    expect(() => getToken()).not.toThrow();
    expect(isExpired('not-a-jwt')).toBe(false);
  });

  test('a token with no exp claim is left to the server to judge', () => {
    localStorage.setItem('token', jwt({ user_id: 1 }));
    expect(getToken()).toBeTruthy();
  });

  test('clearToken removes it', () => {
    localStorage.setItem('token', jwt({ exp: inHours(1) }));
    clearToken();
    expect(localStorage.getItem('token')).toBeNull();
  });
});

describe('isTokenRejection', () => {
  test('recognises simplejwt’s rejection envelope', () => {
    expect(isTokenRejection({ errors: ['Given token not valid for any token type'] })).toBe(true);
    expect(isTokenRejection({ detail: 'Authentication credentials were not provided.' })).toBe(true);
  });

  test('does not fire on an ordinary permission denial', () => {
    expect(isTokenRejection({ message: 'You do not have permission.' })).toBe(false);
    expect(isTokenRejection(null)).toBe(false);
  });
});
