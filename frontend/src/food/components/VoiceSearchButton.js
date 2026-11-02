import { useRef, useState } from 'react';
import { IconButton, Tooltip } from '@mui/material';
import MicRoundedIcon from '@mui/icons-material/MicRounded';
import { keyframes } from '@emotion/react';
import { toast } from 'react-toastify';

const pulse = keyframes`0%{box-shadow:0 0 0 0 rgba(232,69,43,0.5)}70%{box-shadow:0 0 0 12px rgba(232,69,43,0)}100%{box-shadow:0 0 0 0 rgba(232,69,43,0)}`;

// Speech-to-text via the Web Speech API. Defaults to Bangla (bn-BD) so villagers
// can search by voice in their own language; falls back gracefully where the API
// is unavailable (e.g. Firefox, older browsers).
export default function VoiceSearchButton({ onResult, lang = 'bn' }) {
  const [listening, setListening] = useState(false);
  const recRef = useRef(null);
  const SR = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);

  const t = (en, bn) => (lang === 'bn' ? bn : en);
  if (!SR) return null; // hide the mic entirely when unsupported

  const start = () => {
    if (listening) { recRef.current?.stop(); return; }
    const rec = new SR();
    rec.lang = lang === 'bn' ? 'bn-BD' : 'en-US';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e) => {
      const said = e.results?.[0]?.[0]?.transcript?.trim();
      if (said) onResult?.(said);
    };
    rec.onerror = (e) => {
      setListening(false);
      if (e.error === 'not-allowed') toast.error(t('Microphone blocked', 'মাইক্রোফোন ব্লক করা আছে'));
    };
    rec.onend = () => setListening(false);
    recRef.current = rec;
    setListening(true);
    try { rec.start(); } catch { setListening(false); }
  };

  return (
    <Tooltip title={t('Search by voice', 'কণ্ঠে খুঁজুন')}>
      <IconButton onClick={start} size="small"
        sx={{ color: listening ? 'primary.main' : 'text.secondary',
          animation: listening ? `${pulse} 1.3s infinite` : 'none' }}>
        <MicRoundedIcon />
      </IconButton>
    </Tooltip>
  );
}
