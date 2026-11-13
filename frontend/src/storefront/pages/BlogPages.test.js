import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import axios from 'axios';
import { BlogArticle, BlogIndex } from './BlogPages';

jest.mock('axios');
jest.mock('../../nobleseek/ads/AdSlot', () => () => null);
jest.mock('../../nobleseek/ads/adsConfig', () => ({ useAdConfig: () => ({}) }));

beforeEach(() => { jest.clearAllMocks(); window.scrollTo = jest.fn(); });

test('journal loads the next page without losing the archive route', async () => {
  axios.get.mockImplementation((url,options)=>Promise.resolve(url.includes('topics/')?{data:[]}:{data:options.params.page===1?{count:2,next:'next',results:[{id:1,slug:'buying-guide',headline:'A useful buying guide'}]}:{count:2,next:null,results:[{id:2,slug:'care-guide',headline:'Care for your products'}]}}));
  render(<MemoryRouter initialEntries={['/blog']}><BlogIndex /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'A useful buying guide' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /A useful buying guide/ })).toHaveAttribute('href', '/blog/buying-guide');
  fireEvent.click(screen.getByRole('button', { name: /page 2/i }));
  expect(await screen.findByRole('heading', { name: 'Care for your products' })).toBeInTheDocument();
  expect(axios.get).toHaveBeenLastCalledWith(expect.stringContaining('nobleseek/blog/'), { params: { page: 2 } });
});

test('article uses BlogPosting metadata and removes its schema on unmount', async () => {
  axios.get.mockResolvedValue({ data: { data: { slug: 'guide', headline: 'Choosing well', body_html: '<p>Useful advice.</p>', json_ld: { '@type': 'BlogPosting', headline: 'Choosing well' } } } });
  const view = render(<MemoryRouter initialEntries={['/blog/guide']}><Routes><Route path="/blog/:slug" element={<BlogArticle />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Choosing well' })).toBeInTheDocument();
  await waitFor(() => expect(document.querySelector('script[type="application/ld+json"]')).toHaveTextContent('BlogPosting'));
  expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute('href', 'https://www.fabrything.com/blog/guide');
  view.unmount();
  expect(document.querySelector('script[type="application/ld+json"]')).toBeNull();
});

test('missing article receives noindex and a journal return link', async () => {
  axios.get.mockRejectedValue({ response: { status: 404 } });
  render(<MemoryRouter initialEntries={['/blog/missing']}><Routes><Route path="/blog/:slug" element={<BlogArticle />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Story not found' })).toBeInTheDocument();
  await waitFor(() => expect(document.querySelector('meta[name="robots"]')).toHaveAttribute('content', 'noindex,follow'));
  expect(screen.getByRole('link', { name: 'Back to the journal' })).toHaveAttribute('href', '/blog');
});

test('topic filters and pagination retain the selected intent',async()=>{
 axios.get.mockImplementation((url,options)=>Promise.resolve(url.includes('topics/')?{data:[{id:1,name:'Accessories',slug:'accessories',level:0}]}:{data:{results:[{id:1,slug:'guide',headline:'A focused guide'}],next:options.params.page===1?'next':null}}));
 render(<MemoryRouter initialEntries={['/blog/topic/accessories?intent=comparison']}><Routes><Route path="/blog/topic/:topic" element={<BlogIndex/>}/></Routes></MemoryRouter>);
 expect(await screen.findByRole('heading',{name:'A focused guide'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:/page 2/i}));
 await waitFor(()=>expect(axios.get).toHaveBeenLastCalledWith(expect.stringContaining('nobleseek/blog/'),{params:{page:2,topic:'accessories',intent:'comparison'}}));
});

test('structured guides render disclosed merchant links and expandable questions',async()=>{
 const journal={intent:'buying_guide',cluster:[{name:'Accessories',slug:'accessories'}],disclosure:'Affiliate links may earn commission.',sources:[{title:'Product manual',url:'https://example.com/manual'}],products:[{id:'one',title:'Compatible accessory',platform:'fabrything',url:'https://www.fabrything.com/product/accessory',specs:{Fit:'Read the manual'}}],blocks:[{type:'heading',text:'Check compatibility'},{type:'verdict',text:'Use the manufacturer documentation.'},{type:'products',productIds:['one']},{type:'pros_cons',pros:['Documented fit'],cons:['Check the connector']},{type:'image',alt:'Connector details',width:1200,height:675},{type:'faq',items:[{question:'Where is the specification?',answer:'In the product manual.'}]}]};
 axios.get.mockImplementation(url=>Promise.resolve(url.includes('related/')?{data:[]}:{data:{headline:'Choose a compatible accessory',body_html:'<p>Legacy content must not replace the structured guide.</p>',journal}}));
 render(<MemoryRouter initialEntries={['/blog/guide']}><Routes><Route path="/blog/:slug" element={<BlogArticle/>}/></Routes></MemoryRouter>);
 expect(await screen.findByRole('heading',{name:'Choose a compatible accessory'})).toBeInTheDocument();
 expect(screen.getByRole('complementary',{name:'Affiliate disclosure'})).toHaveTextContent('may earn commission');
 expect(screen.getByRole('link',{name:/View on Fabrything/})).toHaveAttribute('rel','nofollow sponsored noopener');
 expect(screen.getByText('Connector details')).toBeInTheDocument();
 fireEvent.click(screen.getByText('Where is the specification?'));
 expect(screen.getByText('In the product manual.')).toBeVisible();
 expect(screen.queryByText('Legacy content must not replace the structured guide.')).not.toBeInTheDocument();
});
