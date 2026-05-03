import { useState, useRef, useEffect } from 'react';

export default function ChatSidebar({ isOpen, onClose, messages, onSendMessage }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input);
    setInput('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{
      ...styles.container,
      transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
    }}>
      {/* Header */}
      <div style={styles.header}>
        <button style={styles.closeButton} onClick={onClose}>
          ← Close
        </button>
        <div style={styles.title}>Chat with AIRIS</div>
      </div>

      {/* Messages */}
      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.emptyState}>
            Start typing to chat with AIRIS...
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={msg.role === 'user' ? styles.userMessage : styles.assistantMessage}
          >
            <div style={styles.messageLabel}>
              {msg.role === 'user' ? 'Myra' : 'AIRIS'}
            </div>
            <div style={styles.messageContent}>{msg.content}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={styles.inputContainer}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          style={styles.input}
          rows={2}
        />
        <button onClick={handleSend} style={styles.sendButton}>
          Send
        </button>
      </div>
    </div>
  );
}

const styles = {
  container: {
    position: 'fixed',
    top: 0,
    right: 0,
    width: '400px',
    height: '100vh',
    background: 'rgba(10, 14, 26, 0.95)',
    backdropFilter: 'blur(20px)',
    borderLeft: '1px solid rgba(102, 126, 234, 0.2)',
    display: 'flex',
    flexDirection: 'column',
    transition: 'transform 0.3s ease',
    zIndex: 100,
  },
  header: {
    padding: '20px',
    borderBottom: '1px solid rgba(102, 126, 234, 0.2)',
  },
  closeButton: {
    background: 'transparent',
    border: 'none',
    color: '#667eea',
    fontSize: '14px',
    cursor: 'pointer',
    marginBottom: '12px',
  },
  title: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#e0e6ed',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  emptyState: {
    color: '#6b7785',
    fontSize: '14px',
    textAlign: 'center',
    marginTop: '40px',
  },
  userMessage: {
    alignSelf: 'flex-end',
    maxWidth: '80%',
  },
  assistantMessage: {
    alignSelf: 'flex-start',
    maxWidth: '80%',
  },
  messageLabel: {
    fontSize: '11px',
    color: '#6b7785',
    marginBottom: '4px',
    fontWeight: '600',
  },
  messageContent: {
    padding: '12px 16px',
    borderRadius: '12px',
    backgroundColor: 'rgba(26, 31, 46, 0.8)',
    border: '1px solid rgba(102, 126, 234, 0.2)',
    color: '#e0e6ed',
    fontSize: '14px',
    lineHeight: '1.6',
    whiteSpace: 'pre-wrap',
  },
  inputContainer: {
    padding: '20px',
    borderTop: '1px solid rgba(102, 126, 234, 0.2)',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  input: {
    padding: '12px 16px',
    backgroundColor: 'rgba(26, 31, 46, 0.5)',
    border: '1px solid rgba(102, 126, 234, 0.3)',
    borderRadius: '8px',
    color: '#e0e6ed',
    fontSize: '14px',
    resize: 'none',
    fontFamily: 'inherit',
    outline: 'none',
  },
  sendButton: {
    padding: '12px 24px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
};
