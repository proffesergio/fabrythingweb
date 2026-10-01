import React, { useMemo } from 'react';
import AdSlot from './AdSlot';

// Splits article HTML by closing </p> and injects AdSlots every N paragraphs.
// Detail page = maximum ad density: top slot handled by page, here we add
// in-article 1 after para 2, in-article 2 mid-way, multiplex near end.
export default function InArticleBody({ html, slots }) {
  const parts = useMemo(() => {
    const chunks = String(html || '').split(/<\/p>/i).filter(Boolean).map(s => `${s}</p>`);
    if (chunks.length <= 3) return [{ type: 'html', key: 'p0', html }];
    const out = [];
    chunks.forEach((c, i) => {
      out.push({ type: 'html', key: `p${i}`, html: c });
      if (i === 1 && slots?.inarticle1) out.push({ type: 'ad', key: 'ad1', slot: slots.inarticle1, format: 'fluid', layout: 'in-article' });
      else if (i === Math.floor(chunks.length * 0.6) && slots?.inarticle2) out.push({ type: 'ad', key: 'ad2', slot: slots.inarticle2, format: 'auto' });
    });
    if (slots?.multiplex) out.push({ type: 'ad', key: 'adx', slot: slots.multiplex, format: 'autorelaxed' });
    return out;
  }, [html, slots]);

  return (
    <div className="ns-article-body">
      {parts.map((p) => p.type === 'ad'
        ? <AdSlot key={p.key} slot={p.slot} format={p.format} layout={p.layout} minHeight={120} />
        : <div key={p.key} dangerouslySetInnerHTML={{ __html: p.html }} />)}
    </div>
  );
}
