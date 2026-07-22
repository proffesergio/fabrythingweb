// Single owner of the stored access token.
//
// An *expired* JWT is worse than no token at all. It stays in localStorage
// forever (the app stores no refresh token, so nothing ever renews or clears
// it) and every request keeps attaching it, so the server rejects calls that
// would happily have served an anonymous caller. That is exactly what the
// production console showed: `food/notifications/`, `food/loyalty/`,
// `getMenus/` and — worst of all — a guest's `POST food/orders/` all failing
// 401 with "Given token not valid for any token type". A visitor who once
// logged in months ago simply could not order.
//
// The rule here: a token is only worth sending while it is still valid, and a
// token the server rejects is dead and must be dropped, not retried.
export const TOKEN_KEY = 'token';

// Decode a JWT payload without a library. Returns null for anything that is not
// a well-formed three-part token — a garbage value in storage is treated the
// same as no value.
function payloadOf(jwt) {
  try {
    const body = jwt.split('.')[1];
    if (!body) return null;
    const json = atob(body.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

// A little slack, so a token that expires mid-flight is treated as already gone
// rather than producing a 401 we then have to recover from.
const SKEW_MS = 5000;

export function isExpired(jwt) {
  const exp = payloadOf(jwt)?.exp;
  // No `exp` claim: we cannot prove it is dead, so let the server decide.
  return typeof exp === 'number' && Date.now() + SKEW_MS >= exp * 1000;
}

export function clearToken() {
  try { localStorage.removeItem(TOKEN_KEY); } catch { /* private mode */ }
}

/** The token to send, or '' when there is none worth sending. Self-cleaning:
 *  an expired token is removed here rather than left to fail every request. */
export function getToken() {
  let raw = null;
  try { raw = localStorage.getItem(TOKEN_KEY); } catch { return ''; }
  if (!raw) return '';
  if (isExpired(raw)) { clearToken(); return ''; }
  return raw;
}

/** True when the user is signed in *and* the session is still good. Use this
 *  instead of reading localStorage directly, or the UI shows a signed-in shell
 *  around endpoints that answer 401. */
export function isSignedIn() {
  return !!getToken();
}

/** Did the server reject us specifically because the token is bad (as opposed
 *  to this endpoint simply requiring a login we do not have)? */
export function isTokenRejection(errData) {
  const blob = JSON.stringify(errData || '');
  return /token|credentials/i.test(blob);
}
