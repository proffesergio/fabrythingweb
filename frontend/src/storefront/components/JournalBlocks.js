import React from 'react';

export const guideContents = blocks => blocks.flatMap((b,i) => {
 const title=b.type==='heading'?b.text:({verdict:'Quick verdict',comparison:'Compare your options',products:'Products in this guide',pros_cons:'The trade-offs',faq:'Common questions'})[b.type];
 return title?[{id:`section-${i}`,title}]:[];
});
export function JournalImage({image,priority=false}) {
 if(!image.src) return <figure className="journal-image-plan" style={{aspectRatio:`${image.width}/${image.height}`}}><span>Illustration planned</span><figcaption>{image.alt}</figcaption></figure>;
 return <figure className="journal-image"><img src={image.src} alt={image.alt} width={image.width} height={image.height} loading={priority?'eager':'lazy'} fetchpriority={priority?'high':undefined} decoding="async" srcSet={image.variants?.map(v=>`${v.src} ${v.width}w`).join(', ')||undefined} sizes="(max-width: 800px) 100vw, 800px"/></figure>;
}
function ProductLink({product,children}) {return <a className="journal-cta" href={product.url} rel="nofollow sponsored noopener">{children||`View on ${product.platform==='fabrything'?'Fabrything':product.platform}`} <span aria-hidden="true">↗</span></a>;}
function ProductDetails({product}) {return <><dl>{Object.entries(product.specs||{}).map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>{product.review&&<blockquote><p>{product.review.body}</p><cite>{product.review.author} · {product.review.datePublished} · <a href={product.review.sourceUrl} rel="nofollow noopener">Review source</a></cite></blockquote>}</>;}
export default function JournalBlocks({journal}) {
 const products=new Map(journal.products.map(p=>[p.id,p]));
 return <div className="journal-prose">{journal.blocks.map((b,i)=>{
  const id=`section-${i}`;
  if(b.type==='heading')return <h2 id={id} key={id}>{b.text}</h2>;
  if(b.type==='paragraph')return <p key={id}>{b.text}</p>;
  if(b.type==='verdict')return <aside className="journal-verdict" id={id} key={id}><span className="journal-eyebrow">THE SHORT ANSWER</span><h2>Quick verdict</h2><p>{b.text}</p></aside>;
  if(b.type==='image')return <JournalImage key={id} image={b} priority={i===journal.blocks.findIndex(x=>x.type==='image'&&x.src)}/>;
  if(b.type==='pros_cons')return <section className="journal-tradeoffs" id={id} key={id}><h2>The trade-offs</h2><div><section><h3>Why it may work</h3><ul>{b.pros.map((s,n)=><li key={n}>{s}</li>)}</ul></section><section><h3>Keep in mind</h3><ul>{b.cons.map((s,n)=><li key={n}>{s}</li>)}</ul></section></div></section>;
  if(b.type==='faq')return <section className="journal-faq" id={id} key={id}><h2>Common questions</h2>{b.items.map((x,n)=><details key={n}><summary>{x.question}</summary><p>{x.answer}</p></details>)}</section>;
  const selected=(b.productIds||[]).map(pid=>products.get(pid)).filter(Boolean);
  if(b.type==='comparison')return <section id={id} key={id}><h2>Compare your options</h2><div className="journal-table-wrap" tabIndex={0} role="region" aria-label="Product comparison"><table><caption>Compare supported details. Check each website for the current price.</caption><thead><tr><th scope="col">Product</th><th scope="col">Details & limitations</th><th scope="col">Explore</th></tr></thead><tbody>{selected.map(p=><tr key={p.id}><th scope="row">{p.title}</th><td><ProductDetails product={p}/></td><td><ProductLink product={p}/></td></tr>)}</tbody></table></div></section>;
  if(b.type==='products')return <section id={id} key={id}><h2>Products in this guide</h2><div className="journal-products">{selected.map(p=><article key={p.id} className="journal-product-card">{p.image&&<img src={p.image} alt={p.imageAlt||p.title} width={400} height={300} loading="lazy" decoding="async"/>}<span className="journal-eyebrow">{p.platform}</span><h3>{p.title}</h3><ProductDetails product={p}/><ProductLink product={p}/></article>)}</div><p className="journal-caption">Availability and prices can change. Check the destination website for the updated price.</p></section>;
  return null;
 })}</div>;
}
