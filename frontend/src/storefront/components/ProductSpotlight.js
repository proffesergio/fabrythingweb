import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowForward, ArrowOutward, PauseCircleOutline, PlayCircleOutline } from '@mui/icons-material';
import { useReducedMotion } from 'framer-motion';
import './ProductSpotlight.css';

export default function ProductSpotlight({ products = [], loading = false }) {
    const reduceMotion = useReducedMotion();
    const [paused, setPaused] = useState(false);
    const [selected, setSelected] = useState(0);
    const [failedImages, setFailedImages] = useState([]);
    const seen = new Set();
    const picks = products.flatMap((product) => {
        if (!product?.slug || seen.has(product.slug)) return [];
        seen.add(product.slug);
        const images = Array.isArray(product.image) ? product.image : [];
        const image = images.find((url) => typeof url === 'string' && /^(https?:\/\/|\/[^/])/.test(url) && !failedImages.includes(url));
        return image ? [{ ...product, image }] : [];
    }).slice(0, 3);
    const active = picks[selected % (picks.length || 1)];
    const motionOff = paused || reduceMotion;
    const productUrl = active ? `/product/${encodeURIComponent(active.slug)}` : '/shop';

    return <section className={`product-spotlight${motionOff ? ' product-spotlight--paused' : ''}`} aria-labelledby="product-spotlight-heading">
        <div className="product-spotlight__inner">
            <div className="product-spotlight__copy">
                <h2 id="product-spotlight-heading">Everyday style.<br /><span>A fresh perspective.</span></h2>
                <p>Discover clothing and essentials from the Fabrything catalog.</p>
                <div className="product-spotlight__actions">
                    <Link className="product-spotlight__primary" to="/shop">Explore products <ArrowForward fontSize="small" /></Link>
                    <a className="product-spotlight__secondary" href="#popular-products">See what is new</a>
                </div>
                <button className="product-spotlight__motion" type="button" disabled={!!reduceMotion}
                    aria-label={motionOff ? 'Resume banner animation' : 'Pause banner animation'} aria-pressed={motionOff}
                    onClick={() => setPaused((value) => !value)}>
                    {motionOff ? <PlayCircleOutline fontSize="small" /> : <PauseCircleOutline fontSize="small" />}
                    {reduceMotion ? 'Reduced motion enabled' : `Animation: ${motionOff ? 'off' : 'on'}`}
                </button>
            </div>
            <div className="product-spotlight__visual">
                <div className="product-spotlight__stage" aria-busy={loading && !active}>
                    {active ? <Link to={productUrl} aria-label={`View ${active.name}`}>
                        <img key={active.image} src={active.image} alt={active.name} width="560" height="700" loading="lazy" decoding="async"
                            onError={() => setFailedImages((current) => current.includes(active.image) ? current : [...current, active.image])} />
                    </Link> : <div className="product-spotlight__empty">{loading ? 'Loading the collection…' : 'Your next favourite awaits.'}<Link to="/shop">Browse the catalog <ArrowForward fontSize="small" /></Link></div>}
                </div>
                {active && <Link className="product-spotlight__card" to={productUrl}>
                    <small><i aria-hidden="true" />From the catalog</small>
                    <h3>{active.name}</h3>
                    <span>View product <ArrowOutward fontSize="small" /></span>
                </Link>}
                {picks.length > 1 && <div className="product-spotlight__choices" role="group" aria-label="Featured products">
                    {picks.map((product, index) => <button key={product.slug} type="button" aria-label={`Show ${product.name}`}
                        aria-pressed={active.slug === product.slug} onClick={() => setSelected(index)}>{String(index + 1).padStart(2, '0')}</button>)}
                </div>}
            </div>
        </div>
    </section>;
}
