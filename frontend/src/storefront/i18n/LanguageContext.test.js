import { render, screen, fireEvent } from '@testing-library/react';
import { LanguageProvider, useLanguage, useT } from './LanguageContext';
import { DEFAULT_LANGUAGE, translate } from './strings';

function Probe() {
    const { lang, setLang } = useLanguage();
    const t = useT();
    return (
        <div>
            <span data-testid="lang">{lang}</span>
            <span data-testid="title">{t('printing.title')}</span>
            <span data-testid="missing">{t('no.such.key')}</span>
            <button onClick={() => setLang('en')}>english</button>
        </div>
    );
}

beforeEach(() => window.localStorage.clear());

// Most Fabrything customers read Bangla — the default must not be English.
test('defaults to Bangla', () => {
    render(<LanguageProvider><Probe /></LanguageProvider>);
    expect(screen.getByTestId('lang').textContent).toBe('bn');
    expect(DEFAULT_LANGUAGE).toBe('bn');
    expect(screen.getByTestId('title').textContent).toBe('কাস্টম প্রিন্টিং');
});

test('switching language re-renders and persists the choice', () => {
    render(<LanguageProvider><Probe /></LanguageProvider>);
    fireEvent.click(screen.getByText('english'));
    expect(screen.getByTestId('title').textContent).toBe('Custom Printing');
    expect(window.localStorage.getItem('sf_lang')).toBe('en');
});

test('a saved choice wins over the default on next load', () => {
    window.localStorage.setItem('sf_lang', 'en');
    render(<LanguageProvider><Probe /></LanguageProvider>);
    expect(screen.getByTestId('lang').textContent).toBe('en');
});

test('an unknown saved value falls back to the default rather than breaking', () => {
    window.localStorage.setItem('sf_lang', 'martian');
    render(<LanguageProvider><Probe /></LanguageProvider>);
    expect(screen.getByTestId('lang').textContent).toBe('bn');
});

// A missing translation must degrade visibly, never render blank.
test('a missing key falls back to English then to the key itself', () => {
    render(<LanguageProvider><Probe /></LanguageProvider>);
    expect(screen.getByTestId('missing').textContent).toBe('no.such.key');
    expect(translate('printing.tab.mine', 'en')).toBe('My Requests');
});

test('every English key has a Bangla translation', () => {
    // Guards the workflow: a page translated in English but not Bangla would
    // silently show English to a Bangla-default audience.
    const { strings } = require('./strings');
    const missing = Object.keys(strings.en).filter((k) => !(k in strings.bn));
    expect(missing).toEqual([]);
});
