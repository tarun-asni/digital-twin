import React, { useEffect, useState, useRef } from 'react';
import { sendVoiceCommand } from '../utils/appClient';
import '../CameraDetail.css';

const VoiceCommandPanel = ({ onResponse }) => {
  const [transcript, setTranscript] = useState('');
  const [status, setStatus] = useState('🎙️ Say "hello applied" to activate...');
  const [isActive, setIsActive] = useState(false);
  const WAKE_WORD = 'hello applied';
  const isActiveRef = useRef(false);
  const recognitionRef = useRef(null);

  const handleCommand = async (command) => {
    setTranscript(command);
    setStatus('Sending command to server...');
    isActiveRef.current = true;

    try {
      const result = await sendVoiceCommand(command);
      if (result) {
        setStatus('✅ Command processed. Listening continues...');
        if (Array.isArray(result) && result.length > 0) {
        if (onResponse) {
          onResponse({
            command: `${WAKE_WORD} ${command}`,
            alerts: result
          });
        }
      }
        if (Array.isArray(result) && result.length === 0) {
          setStatus(`No alerts found for ${command}.`);
        }

      } else {
        setStatus('❌ Failed to process command.');
      }
    } catch (err) {
      console.error('Command error:', err);
      setStatus('⚠️ Error sending command.');
    }
  };

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatus('Speech recognition not supported.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const heard = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
      console.log('Heard:', heard);

      let command = '';
      if (heard.includes(WAKE_WORD)) {
        setStatus('Wake word detected! Listening continues...');
        isActiveRef.current = true;
        setIsActive(true);
        command = heard.split(WAKE_WORD).pop().trim();
      } else if (isActiveRef.current) {
        command = heard;
      }

      if (command) {
        setTranscript(command);
        setStatus('🎤 Heard command. Processing...');
        handleCommand(command);
      }
    };

    recognition.onerror = (e) => {
      console.error('Recognition error:', e);
      setStatus(`Error: ${e.error}`);
    };

    recognition.onend = () => {
      console.log('Recognition ended. Restarting...');
      try {
        recognition.start();
        setStatus('🎤 Listening restarted...');
      } catch (err) {
        console.warn('Restart failed:', err);
        setStatus('⚠️ Unable to restart listening.');
      }
    };

    try {
      recognition.start();
    } catch (err) {
      console.warn('Initial start failed:', err);
    }

    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
    };
  }, []);

  const handleMicClick = () => {
    const recognition = recognitionRef.current;
    if (!recognition) return;

    try {
      recognition.stop();
    } catch (err) {
      console.warn('Stop before manual start failed:', err);
    }

    setTimeout(() => {
      try {
        recognition.start();
        setStatus('🎤 Manual listening restarted...');
        setIsActive(true);
        isActiveRef.current = true;
      } catch (err) {
        console.warn('Manual start failed:', err);
        setStatus('⚠️ Unable to start recognition manually.');
      }
    }, 6);
  };

  return (
    <div className="voice-panel center-panel">
      <p><strong>Status:</strong> {status}</p>

      {isActive && (
        <div className="input-wrapper">
          <input
            type="text"
            value={transcript}
            placeholder="Speak your command..."
            readOnly
            className="voice-input"
          />
        </div>
      )}

      <div className="button-wrapper">
        <button onClick={handleMicClick} className="mic-button">
          🎤 Tap to Listen
        </button>
      </div>
    </div>
  );
};

export default VoiceCommandPanel;