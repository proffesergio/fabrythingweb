// Console output that must not reach a production build.
//
// The live admin panel was printing every API response body (customer records
// included), the decoded JWT claims on each auth check, and the login response
// -- which carries the access AND refresh tokens -- straight to the browser
// console. Anyone with the devtools open, or any extension reading console
// output, got all of it.
//
// CRA sets NODE_ENV=production for `react-scripts build`, so these calls are
// also dead code the minifier drops from the shipped bundle.
export const devLog = (...args) => {
  if (process.env.NODE_ENV !== 'production') {
    // eslint-disable-next-line no-console
    console.log(...args);
  }
};

/** Errors worth keeping in production, but never with a payload attached. */
export const devWarn = (...args) => {
  if (process.env.NODE_ENV !== 'production') {
    // eslint-disable-next-line no-console
    console.warn(...args);
  }
};
