import { useEffect } from 'react';

let injected = false;

// News-only typography: Noto Serif Bengali (headlines) + Hind Siliguri
// (body/UI). Injected from the portal layout so shop routes never pay for it.
export default function NewsFonts() {
  useEffect(() => {
    if (injected) return;
    injected = true;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css2?family=Noto+Serif+Bengali:wght@600;700;800;900&family=Hind+Siliguri:wght@400;500;600;700&display=swap';
    document.head.appendChild(link);
    const style = document.createElement('style');
    style.setAttribute('data-ns-fonts', '1');
    style.textContent = `
      .ns-serif { font-family: 'Noto Serif Bengali', 'Hind Siliguri', sans-serif !important; }
      .ns-sans { font-family: 'Hind Siliguri', 'Noto Sans Bengali', sans-serif !important; }
      .ns-dropcap::first-letter {
        font-family: 'Noto Serif Bengali', serif;
        font-weight: 900; font-size: 3.1em; float: left;
        line-height: 0.85; padding-right: 8px; color: #F2631F;
      }
      .ns-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
      .ns-clamp-3 { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
      @keyframes ns-ticker-scroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
      .ns-ticker-track { display: inline-flex; white-space: nowrap; animation: ns-ticker-scroll 60s linear infinite; }
      .ns-ticker-track:hover { animation-play-state: paused; }
    `;
    document.head.appendChild(style);
  }, []);
  return null;
}
