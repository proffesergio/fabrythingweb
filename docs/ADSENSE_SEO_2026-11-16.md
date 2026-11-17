# AdSense, indexing and Facebook preview repair

## Findings

The owner’s latest Search Console report supersedes the older 453 exclusions:
one redirected URL and 16 discovered URLs remain; crawled-but-not-indexed is zero.
The previously reported 391 server errors and 21 soft 404s must not be presented
as current failures without current example URLs and crawl dates.

Read-only live checks before this repair found:

- `https://www.fabrything.com/ads.txt` and the NobleSeek subdomain both returned
  HTTP 200, `text/plain`, with publisher `pub-1712742966437949`. The apex
  redirected successfully to the www file. The dashboard's “not found” value
  did not describe the responses observed during this audit.
- Main and news sitemaps returned 200, as did the API health check and sampled
  products/blog articles. This sample cannot establish every reported URL's status.
- News articles, the news homepage and trust pages returned the same generic
  2,789-byte React shell, without article titles, canonical links or Open Graph
  metadata in their initial HTML. A nonexistent news article also returned 200.
- The server-rendered blog lacked the AdSense verification metadata/script.

## Repair

News now has server-rendered public documents, sanitized article bodies, real
publication dates, sources, image credits, title/description/canonical metadata,
NewsArticle structured data and Open Graph/Twitter cards. The same document is
served to readers and crawlers. The existing React portal enhances it after its
data loads; script or API failure preserves readable HTML. Drafts, scheduled
articles, blog articles on news routes and unknown news slugs return real 404s.
Transient upstream outages remain retryable 503s rather than empty 200s.

Archives have crawlable page links and matching server/client pagination, with
12 articles per page. Search and empty results are noindex. The existing news
sitemap retains older published articles and adds news extension metadata to
up to 1,000 articles published in the last two days.

`ads.txt` contains the exact supplied authorization record, without a trailing
semicolon. Its response has an explicit text content type and short cache age.
The supplied asynchronous AdSense script is in the public app head and the
server-rendered blog head; the existing loader recognizes it to avoid duplicates.
Blog pages also receive the explicit publisher verification meta tag.

## Actions in Google accounts

1. In AdSense → Sites → fabrything.com, select **Check for updates** for ads.txt.
   Verify the publisher is the same account. Do not remove/re-add a site that is
   already being reviewed. Complete any outstanding account/payments setup and
   check Policy center. Google's published review guidance says a few days,
   sometimes two to four weeks; there is no approval guarantee.
2. In Search Console, submit the canonical sitemaps in the corresponding property:
   `https://www.fabrything.com/sitemap.xml` and
   `https://nobleseek.fabrything.com/sitemap.xml`.
   A verified domain property covers both hosts. Inspect a representative URL
   from the 16 discovered pages using **Test live URL**, check the rendered HTML,
   then request indexing for important pages. Validate old error groups only if
   they remain current and their example URLs are repaired. A redirect remains
   excluded intentionally; inspect its final canonical destination instead.
3. Before monetizing, configure a Google-certified CMP, including the appropriate
   European regulations message for visitors in the EEA, UK and Switzerland.
   A custom consent flag or a script tag alone does not supply a certified CMP.
4. After the site is **Ready**, create real ad units and configure editorial
   placements. Keep Auto ads off if ads should be limited to news/blog articles,
   or configure and verify account-side page exclusions before enabling them.
   Verification code is not itself evidence of approval or an active manual unit.
   Do not show ads on empty/error/login/checkout pages; avoid excessive ad density,
   misleading placements, clicking your own ads or asking readers to click.

## Editorial requirements

Review news and blog articles for original value, factual accuracy, clear
editorial responsibility, attributable sources, useful titles, accessible images
and rights to reuse both text and photos. Credit alone does not license a photo.
Human review must actually occur if the published editorial policy promises it.
Improve or withdraw low-value material deliberately; do not bulk-delete content
solely to reduce an exclusion count. Mass rewriting or translating feeds without
additional reader value can violate Google's scaled-content and publisher rules.

Keep About, Contact, Privacy, editorial/corrections policies and advertising or
affiliate disclosures accurate. Add concrete experience, comparisons, reporting
or tested guidance where useful. Google has no magical SEO word-count target.
Neither all URLs being indexed nor an arbitrary article count guarantees AdSense
approval. Indexing, ranking and AdSense review are separate Google decisions.

## Facebook

The preview tags must be in the initial HTML because a JavaScript-only metadata
update does not reliably reach the sharing crawler. News now supplies canonical
URL, article type, title, description, absolute preview image and image alt text.
Use real, publicly fetchable article images. For previously shared links, paste
the canonical URL into Facebook Sharing Debugger and select **Scrape Again**.
Retest the website's Facebook share control and a newly pasted link. Meta decides
whether to display a card in each placement, including comments; website markup
cannot force a preview in every comment or app version.

## Primary references

- [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=en)
- [AdSense site statuses](https://support.google.com/adsense/answer/12170222?hl=en)
- [Ads.txt guide and recheck](https://support.google.com/adsense/answer/12171612?hl=en-GB)
- [Ads.txt crawl requirements](https://support.google.com/adsense/answer/7679060?hl=en)
- [Publisher policies](https://support.google.com/publisherpolicies/answer/10502938?hl=en-GB)
- [Google CMP](https://support.google.com/adsense/answer/16918505?hl=en)
- [News sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap)
- [Search spam policies](https://developers.google.com/search/docs/essentials/spam-policies)
- [Meta sharing markup](https://developers.facebook.com/documentation/sharing/webmasters)

## Verified release

Backend `dpl_DgbvyQeK5ARK8W2vhftXWBmYYbxK` and frontend
`dpl_51GK9W8La7mVBJt2wgx9SNfV94PD` are Ready on the existing production domains.
The current frontend deployment adds the approved desktop newspaper UI over the
prior SEO release (`dpl_7wimyCLNz6ipE5e94VCsFDfcj6zX`). Direct CLI upload initially
exposed CRLF line endings in the shell build script; the release script was
normalized to LF and the corrected build succeeded.

Focused checks: 36 backend tests, 14 Node tests, 34 React tests and an isolated
production build passed. Existing CRA/Browserslist and React act warnings remain.
Live samples confirm exact plain-text ads.txt on apex/www/news, one publisher
script and meta tag on storefront/news/blog documents, canonical article metadata
in initial HTML, and a real 404 with noindex for a nonexistent news article.
Both sampled news documents and both preview images returned 200 with the
documented Facebook crawler user-agent (JPEG/WebP respectively). This is a public
fetch check, not a successful logged-in Sharing Debugger re-scrape or a promise
that Meta will display a card in every comment.

## Desktop newspaper UI follow-up

The owner approved Superdesign draft
`361ec0de-05f0-4501-8301-aaa76fcc02da`. The dense lead/secondary/rail layout,
12-story latest row, topic sections and compact header/footer are implemented.
29 focused React tests, targeted lint, an isolated production build and local
1440/390/320 browser checks pass with 51 headlines and no horizontal overflow or
page exceptions.

Live verification after frontend `dpl_51GK9W8La7mVBJt2wgx9SNfV94PD` became Ready:
1440/390/320 render the dense layout without overflow or page exceptions, and a
JavaScript-disabled article remains readable. Publisher file, sitemaps (945
storefront/643 news URLs), canonicals, the noindex 404 and API health remain
unchanged. These checks do not guarantee ad approval, indexing, ranking or
third-party previews.
