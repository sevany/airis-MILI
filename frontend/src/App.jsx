import { useState, useEffect } from 'react';
import VoiceVisualization from './components/VoiceVisualization';
import ChatSidebar from './components/ChatSidebar';
import VoiceButton from './components/VoiceButton';
import { api } from './utils/api';

function App() {
  const [voiceStatus, setVoiceStatus] = useState('idle'); // idle, listening, speaking
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isOnline, setIsOnline] = useState(false);

  // Check backend health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const health = await api.health();
        setIsOnline(health?.components?.ollama?.status === 'ok');
      } catch {
        setIsOnline(false);
      }
    };
    
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleVoiceInput = async () => {
    // Phase 2: This will trigger Whisper STT
    // For now, just open chat
    setChatOpen(true);
  };

  const handleSendMessage = async (message) => {
    if (!message.trim()) return;

    // Add user message
    const userMsg = { role: 'user', content: message };
    setMessages(prev => [...prev, userMsg]);

    // Add placeholder for AIRIS
    const airisIndex = messages.length + 1;
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    setVoiceStatus('speaking');

    // Audio queue for streaming TTS
    const audioQueue = [];
    let isPlaying = false;

    const playNextAudio = async () => {
      if (isPlaying || audioQueue.length === 0) return;
      
      isPlaying = true;
      const audioBase64 = audioQueue.shift();
      
      try {
        const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
        
        audio.onended = () => {
          isPlaying = false;
          playNextAudio();
        };
        
        audio.onerror = () => {
          isPlaying = false;
          playNextAudio();
        };
        
        await audio.play();
      } catch (error) {
        console.error('Audio playback error:', error);
        isPlaying = false;
        playNextAudio();
      }
    };

    const queueAudioForText = async (text) => {
      if (!text.trim()) return;
      
      try {
        const audioBase64 = await api.synthesize(text);
        audioQueue.push(audioBase64);
        playNextAudio();
      } catch (error) {
        console.error('TTS queue error:', error);
      }
    };

    try {
      let fullResponse = '';
      let sentenceBuffer = '';
      
      await api.chat(message, (chunk) => {
        fullResponse += chunk;
        sentenceBuffer += chunk;
        
        setMessages(prev => {
          const updated = [...prev];
          updated[airisIndex] = { role: 'assistant', content: fullResponse };
          return updated;
        });

        // Check for complete sentences (faster trigger)
        const sentenceEnders = /[.!?,\n]/;
        if (sentenceEnders.test(chunk)) {
          const sentence = sentenceBuffer.trim();
          if (sentence.length > 5) { // Reduced from 10 to 5
            queueAudioForText(sentence);
            sentenceBuffer = '';
          }
        }
        
        // Also trigger if buffer gets too long (don't wait forever)
        if (sentenceBuffer.length > 50) {
          const sentence = sentenceBuffer.trim();
          queueAudioForText(sentence);
          sentenceBuffer = '';
        }
      });

      // Speak any remaining text
      if (sentenceBuffer.trim().length > 0) {
        queueAudioForText(sentenceBuffer.trim());
      }

      setVoiceStatus('idle');
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => {
        const updated = [...prev];
        updated[airisIndex] = { 
          role: 'assistant', 
          content: 'Error: ' + error.message 
        };
        return updated;
      });
      setVoiceStatus('idle');
    }
  };

  return (
    <div style={styles.container}>
      {/* Background Visualization */}
      <VoiceVisualization status={voiceStatus} />

      {/* Status Indicator */}
      <div style={styles.statusContainer}>
        <div style={isOnline ? styles.statusOnline : styles.statusOffline}>
          <span style={styles.statusDot}>●</span>
          <span style={styles.statusText}>
            {isOnline ? 'AIRIS Online' : 'AIRIS Offline'}
          </span>
        </div>
      </div>

      {/* Twistcode Logo - Top Right */}
      <div style={styles.logoContainer}>
        <img 
          src="/logo.png" 
          alt="Twistcode" 
          style={styles.logo}
        />
      </div>

      {/* Voice Status Text - REMOVED */}
      {/* <div style={styles.voiceStatusContainer}>
        <div style={styles.airisName}>AIRIS</div>
        <div style={styles.voiceStatusText}>
          {voiceStatus === 'listening' && 'Listening...'}
          {voiceStatus === 'speaking' && 'Speaking...'}
          {voiceStatus === 'idle' && 'Ready'}
        </div>
      </div> */}

      {/* Voice Button */}
      <VoiceButton 
        status={voiceStatus}
        onClick={handleVoiceInput}
      />

      {/* Chat Button (bottom right) */}
      {!chatOpen && (
        <button 
          style={styles.chatToggle}
          onClick={() => setChatOpen(true)}
        >
          Chat
        </button>
      )}

      {/* Sliding Chat Sidebar */}
      <ChatSidebar
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        messages={messages}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}

const styles = {
  container: {
    width: '100vw',
    height: '100vh',
    backgroundColor: '#000',
    position: 'relative',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusContainer: {
    position: 'absolute',
    top: '20px',
    left: '20px',
  },
  statusOnline: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    background: 'rgba(16, 185, 129, 0.1)',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    borderRadius: '20px',
  },
  statusOffline: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '20px',
  },
  statusDot: {
    color: '#10b981',
    fontSize: '16px',
  },
  statusText: {
    color: '#e0e6ed',
    fontSize: '12px',
    fontWeight: '600',
  },
  logoContainer: {
    position: 'absolute',
    top: '20px',
    right: '20px',
  },
  logo: {
    height: '50px',
    width: 'auto',
    opacity: 0.9,
  },
  voiceStatusContainer: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    textAlign: 'center',
    pointerEvents: 'none',
    marginTop: '-150px',
  },
  airisName: {
    fontSize: '72px',
    fontWeight: 'bold',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    letterSpacing: '8px',
    marginBottom: '16px',
  },
  voiceStatusText: {
    fontSize: '18px',
    color: 'rgba(255, 255, 255, 0.6)',
    textTransform: 'uppercase',
    letterSpacing: '4px',
  },
  chatToggle: {
    position: 'absolute',
    bottom: '30px',
    right: '30px',
    padding: '12px 24px',
    background: 'rgba(102, 126, 234, 0.2)',
    border: '1px solid rgba(102, 126, 234, 0.4)',
    borderRadius: '24px',
    color: '#667eea',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
};

export default App;
