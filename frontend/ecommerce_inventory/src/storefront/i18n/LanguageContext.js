import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { DEFAULT_LANGUAGE, LANGUAGES, translate } from './strings';

const STORAGE_KEY = 'sf_lang';

const LanguageContext = createContext({
    lang: DEFAULT_LANGUAGE,
    setLang: () => {},
    t: (key) => key,
});

/**
 * Storefront language. Defaults to Bangla because that is what most Fabrything
 * customers read; a visitor's explicit choice is remembered in localStorage and
 * always wins afterwards.
 *
 * Deliberately NOT auto-detecting from the browser: a Bangladeshi customer on a
 * phone shipped with English locale still wants Bangla here, and silently
 * flipping the language based on a device setting is more confusing than a
 * stable default plus a visible switch.
 */
export function LanguageProvider({ children }) {
    const [lang, setLangState] = useState(() => {
        try {
            const saved = window.localStorage.getItem(STORAGE_KEY);
            if (saved && LANGUAGES.some((l) => l.code === saved)) return saved;
        } catch {
            // Private mode / storage disabled — fall through to the default.
        }
        return DEFAULT_LANGUAGE;
    });

    const setLang = useCallback((next) => {
        setLangState(next);
        try {
            window.localStorage.setItem(STORAGE_KEY, next);
        } catch {
            // Not fatal: the choice just won't survive a reload.
        }
    }, []);

    // Keeps screen readers and browser translation prompts honest about what
    // language the page is actually in.
    useEffect(() => {
        document.documentElement.lang = lang;
    }, [lang]);

    const value = useMemo(
        () => ({ lang, setLang, t: (key) => translate(key, lang) }),
        [lang, setLang],
    );

    return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
    return useContext(LanguageContext);
}

/** Convenience for the common case: `const t = useT();` */
export function useT() {
    return useContext(LanguageContext).t;
}
