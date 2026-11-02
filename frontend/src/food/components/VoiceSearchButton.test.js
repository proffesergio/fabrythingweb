import { render, screen, fireEvent } from '@testing-library/react';
import VoiceSearchButton from './VoiceSearchButton';

jest.mock('react-toastify', () => ({ toast: { error: jest.fn() } }));

afterEach(() => { delete window.SpeechRecognition; delete window.webkitSpeechRecognition; });

test('renders nothing when the Web Speech API is unavailable', () => {
  const { container } = render(<VoiceSearchButton onResult={jest.fn()} />);
  expect(container).toBeEmptyDOMElement();
});

test('starts recognition in bn-BD and returns the transcript', () => {
  const started = { lang: null };
  class FakeSR {
    start() { started.lang = this.lang; this.onresult({ results: [[{ transcript: ' বিরিয়ানি ' }]] }); this.onend(); }
    stop() {}
  }
  window.webkitSpeechRecognition = FakeSR;
  const onResult = jest.fn();
  render(<VoiceSearchButton onResult={onResult} lang="bn" />);
  fireEvent.click(screen.getByRole('button'));
  expect(started.lang).toBe('bn-BD');
  expect(onResult).toHaveBeenCalledWith('বিরিয়ানি');   // trimmed transcript
});
