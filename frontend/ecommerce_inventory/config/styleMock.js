// Jest can't parse the CSS that `swiper/css*` resolves to. Webpack handles it
// in the real build; tests only need the import not to explode.
module.exports = {};
