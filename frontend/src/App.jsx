import { useState, useEffect, useRef } from 'react';
import VoiceVisualization from './components/VoiceVisualization';
import ChatSidebar from './components/ChatSidebar';
import { api } from './utils/api';

function App() {
  const [voiceStatus, setVoiceStatus] = useState('idle');
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isOnline, setIsOnline] = useState(false);
  const [currentAudio, setCurrentAudio] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  
  // Recording state
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  // Check backend health
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

  const toggleRecording = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      
      const options = { mimeType: 'audio/webm;codecs=opus' };
      const recorder = new MediaRecorder(stream, options);
      
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };
      
      recorder.onstop = async () => {
        console.log('🔇 Recording stopped');
        
        if (chunksRef.current.length > 0) {
          const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm;codecs=opus' });
          console.log('📦 Blob size:', audioBlob.size);
          
          if (audioBlob.size > 0) {
            await transcribeAndRespond(audioBlob);
          }
        }
        
        // Stop stream
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
        }
      };
      
      recorder.start(500);
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      setVoiceStatus('listening');
      console.log('🎤 Recording started');
      
    } catch (error) {
      console.error('❌ Microphone access error:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setVoiceStatus('idle');
    }
  };

  const transcribeAndRespond = async (audioBlob) => {
    try {
      console.log('📤 Sending to STT...');
      
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const response = await fetch('http://localhost:5000/api/stt', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      console.log('✅ Transcribed:', result.text);
      
      if (result.text && result.text.trim().length > 0) {
        setChatOpen(true);
        await handleSendMessage(result.text);
      } else {
        console.log('⚠️ Empty transcription');
        setVoiceStatus('idle');
      }
      
    } catch (error) {
      console.error('❌ Transcription error:', error);
      setVoiceStatus('idle');
    }
  };

  const handleSendMessage = async (message) => {
    if (!message.trim()) return;

    console.log('💬 Sending message:', message);

    const userMsg = { role: 'user', content: message };
    setMessages(prev => [...prev, userMsg]);

    const airisIndex = messages.length + 1;
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    setVoiceStatus('speaking');

    // Audio queue for TTS
    const audioQueue = [];
    let isPlayingAudio = false;

    const playNextAudio = async () => {
      if (isPlayingAudio || audioQueue.length === 0) return;
      
      isPlayingAudio = true;
      const audioBase64 = audioQueue.shift();
      
      try {
        const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
        setCurrentAudio(audio);
        
        audio.onended = () => {
          isPlayingAudio = false;
          setCurrentAudio(null);
          
          if (audioQueue.length === 0) {
            setVoiceStatus('idle');
            console.log('✅ AIRIS finished speaking');
          } else {
            playNextAudio();
          }
        };
        
        audio.onerror = () => {
          isPlayingAudio = false;
          setCurrentAudio(null);
          playNextAudio();
        };
        
        await audio.play();
      } catch (error) {
        console.error('Audio playback error:', error);
        isPlayingAudio = false;
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
        console.error('TTS error:', error);
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

        const sentenceEnders = /[.!?,\n]/;
        if (sentenceEnders.test(chunk)) {
          const sentence = sentenceBuffer.trim();
          if (sentence.length > 5) {
            queueAudioForText(sentence);
            sentenceBuffer = '';
          }
        }
        
        if (sentenceBuffer.length > 50) {
          const sentence = sentenceBuffer.trim();
          queueAudioForText(sentence);
          sentenceBuffer = '';
        }
      });

      if (sentenceBuffer.trim().length > 0) {
        queueAudioForText(sentenceBuffer.trim());
      }

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

  const handleInterrupt = () => {
    console.log('🛑 Interrupt - stopping AIRIS');
    
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      setCurrentAudio(null);
    }
    
    setVoiceStatus('idle');
    
    fetch('http://localhost:5000/api/interrupt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context: 'user interrupted' })
    }).catch(err => console.error('Interrupt notification failed:', err));
  };

  const handleFileUpload = async (file) => {
    // Support both File object and event
    if (file.target) {
      // It's an event from input element
      const files = file.target.files;
      if (!files || files.length === 0) return;
      
      for (let i = 0; i < files.length; i++) {
        await uploadSingleFile(files[i]);
      }
      file.target.value = '';
    } else {
      // It's a File object
      await uploadSingleFile(file);
    }
  };

  const uploadSingleFile = async (file) => {
    console.log(`📄 Uploading: ${file.name}`);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:5000/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      
      if (result.status === 'ok') {
        console.log(`✅ ${file.name} uploaded successfully`);
        
        // Add system message to chat
        setChatOpen(true);
        setMessages(prev => [...prev, {
          role: 'system',
          content: `📄 Learned from: ${file.name}\n✓ ${result.chunks_created} knowledge chunks stored`
        }]);
      } else {
        console.error(`❌ Upload failed: ${result.error}`);
        setMessages(prev => [...prev, {
          role: 'system',
          content: `❌ Failed to upload ${file.name}: ${result.error}`
        }]);
      }
    } catch (error) {
      console.error(`❌ Upload error for ${file.name}:`, error);
      setMessages(prev => [...prev, {
        role: 'system',
        content: `❌ Upload error: ${file.name}`
      }]);
    }
  };

  return (
    <div style={styles.container}>
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

      {/* Twistcode Logo */}
      <div style={styles.logoContainer}>
        <img src="/logo.png" alt="Twistcode" style={styles.logo} />
      </div>

      {/* Record Button (Toggle) */}
      <button
        onClick={toggleRecording}
        style={{
          ...styles.recordButton,
          ...(isRecording ? styles.recordButtonActive : {})
        }}
      >
        {isRecording ? (
          <>
            <div style={styles.recordingDot}></div>
            <span>Stop Recording</span>
          </>
        ) : (
          <>
            <span style={styles.micIcon}>🎤</span>
            <span>Start Recording</span>
          </>
        )}
      </button>

      {/* Interrupt Button (only when AIRIS is speaking) */}
      {voiceStatus === 'speaking' && (
        <button
          onClick={handleInterrupt}
          style={styles.interruptButton}
        >
          🛑 Stop AIRIS
        </button>
      )}

      {/* Speaking Indicator */}
      {voiceStatus === 'speaking' && (
        <div style={styles.speakingIndicator}>
          <div style={styles.speakingDot}></div>
          <div style={styles.speakingText}>AIRIS Speaking...</div>
        </div>
      )}

      {/* Chat Button */}
      {!chatOpen && (
        <button style={styles.chatToggle} onClick={() => setChatOpen(true)}>
          Chat
        </button>
      )}

      {/* Chat Sidebar */}
      <ChatSidebar
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        messages={messages}
        onSendMessage={handleSendMessage}
        onFileUpload={handleFileUpload}
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
  recordButton: {
    position: 'absolute',
    bottom: '40px',
    left: '50%',
    transform: 'translateX(-50%)',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '16px 32px',
    fontSize: '16px',
    fontWeight: '600',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: '2px solid rgba(102, 126, 234, 0.6)',
    borderRadius: '30px',
    color: 'white',
    cursor: 'pointer',
    boxShadow: '0 4px 20px rgba(102, 126, 234, 0.4)',
    transition: 'all 0.3s ease',
    zIndex: 20,
  },
  recordButtonActive: {
    background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
    border: '2px solid rgba(239, 68, 68, 0.6)',
    boxShadow: '0 4px 20px rgba(239, 68, 68, 0.6)',
    animation: 'pulse 1.5s infinite',
  },
  recordingDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    background: '#fff',
    animation: 'pulse 1s infinite',
  },
  micIcon: {
    fontSize: '20px',
  },
  interruptButton: {
    position: 'absolute',
    bottom: '120px',
    left: '50%',
    transform: 'translateX(-50%)',
    padding: '12px 24px',
    fontSize: '14px',
    fontWeight: '600',
    background: 'rgba(239, 68, 68, 0.2)',
    border: '2px solid rgba(239, 68, 68, 0.6)',
    borderRadius: '24px',
    color: '#ef4444',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    zIndex: 20,
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
  speakingIndicator: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '16px 32px',
    background: 'rgba(102, 126, 234, 0.2)',
    border: '2px solid rgba(102, 126, 234, 0.6)',
    borderRadius: '30px',
    backdropFilter: 'blur(10px)',
    zIndex: 10,
  },
  speakingDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    background: '#667eea',
    animation: 'pulse 1.5s infinite',
    boxShadow: '0 0 20px rgba(102, 126, 234, 0.8)',
  },
  speakingText: {
    color: '#667eea',
    fontSize: '16px',
    fontWeight: '600',
    letterSpacing: '1px',
  },
};

export default App;
