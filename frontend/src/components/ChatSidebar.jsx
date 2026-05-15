import { useState, useRef, useEffect } from 'react';

export default function ChatSidebar({ isOpen, onClose, messages, onSendMessage, onFileUpload }) {
  const [input, setInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [width, setWidth] = useState(450); // Resizable width
  const [isResizing, setIsResizing] = useState(false);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const sidebarRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Resize handling
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      
      const newWidth = window.innerWidth - e.clientX;
      // Min 350px, Max 800px
      const clampedWidth = Math.max(350, Math.min(800, newWidth));
      setWidth(clampedWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input);
    setInput('');
    setUploadedFiles([]);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
  };

  const handleFiles = async (files) => {
    console.log(`📎 ${files.length} file(s) attached`);
    
    const fileInfos = files.map(f => ({
      name: f.name,
      size: (f.size / 1024).toFixed(1) + ' KB',
      file: f
    }));
    
    setUploadedFiles(prev => [...prev, ...fileInfos]);
    
    for (const file of files) {
      await onFileUpload(file);
    }
  };

  const removeFile = (index) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Drag & Drop handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    const supportedFiles = files.filter(f => {
      const ext = f.name.split('.').pop().toLowerCase();
      return ['pdf', 'docx', 'txt', 'md'].includes(ext);
    });
    
    if (supportedFiles.length > 0) {
      handleFiles(supportedFiles);
    }
  };

  return (
    <div 
      ref={sidebarRef}
      style={{
        ...styles.container,
        width: `${width}px`,
        transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
      }}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Resize Handle */}
      <div
        style={{
          ...styles.resizeHandle,
          cursor: isResizing ? 'ew-resize' : 'col-resize'
        }}
        onMouseDown={() => setIsResizing(true)}
      >
        <div style={styles.resizeIndicator}>⋮</div>
      </div>

      {/* Drag overlay */}
      {isDragging && (
        <div style={styles.dragOverlay}>
          <div style={styles.dragContent}>
            📄 Drop files here to upload
          </div>
        </div>
      )}

      {/* Header */}
      <div style={styles.header}>
        <button style={styles.closeButton} onClick={onClose}>
          ✕
        </button>
        <div style={styles.title}>AIRIS</div>
        <div style={styles.widthIndicator}>{width}px</div>
      </div>

      {/* Messages */}
      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>💜</div>
            <div style={styles.emptyTitle}>Chat with AIRIS</div>
            <div style={styles.emptySubtitle}>
              Ask questions, upload documents, or just talk
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} style={styles.messageRow}>
            <div style={styles.messageAvatar}>
              {msg.role === 'user' ? '👤' : msg.role === 'system' ? '📄' : '🤖'}
            </div>
            <div style={styles.messageBlock}>
              <div style={styles.messageLabel}>
                {msg.role === 'user' ? 'Myra' : msg.role === 'system' ? 'System' : 'AIRIS'}
              </div>
              <div style={styles.messageContent}>{msg.content}</div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Uploaded Files Preview */}
      {uploadedFiles.length > 0 && (
        <div style={styles.filesPreview}>
          {uploadedFiles.map((file, idx) => (
            <div key={idx} style={styles.fileChip}>
              <span>📄 {file.name}</span>
              <span style={styles.fileSize}>{file.size}</span>
              <button 
                style={styles.fileRemove} 
                onClick={() => removeFile(idx)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input Box */}
      <div style={styles.inputWrapper}>
        <div style={styles.inputBox}>
          <button 
            style={styles.plusButton}
            onClick={() => fileInputRef.current?.click()}
            title="Attach files"
          >
            +
          </button>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />

          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Message AIRIS..."
            style={styles.input}
            rows={1}
          />

          <button 
            onClick={handleSend} 
            style={{
              ...styles.sendButton,
              opacity: input.trim() ? 1 : 0.5
            }}
            disabled={!input.trim()}
          >
            ↑
          </button>
        </div>
        
        <div style={styles.inputHint}>
          Drag files here or click + to upload • PDF, DOCX, TXT, MD
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    position: 'fixed',
    top: 0,
    right: 0,
    height: '100vh',
    background: 'rgba(10, 14, 26, 0.98)',
    backdropFilter: 'blur(20px)',
    borderLeft: '1px solid rgba(102, 126, 234, 0.15)',
    display: 'flex',
    flexDirection: 'column',
    transition: 'transform 0.3s ease',
    zIndex: 100,
  },
  resizeHandle: {
    position: 'absolute',
    left: 0,
    top: 0,
    width: '8px',
    height: '100%',
    background: 'transparent',
    cursor: 'col-resize',
    zIndex: 101,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  resizeIndicator: {
    fontSize: '16px',
    color: 'rgba(102, 126, 234, 0.3)',
    transform: 'rotate(90deg)',
    pointerEvents: 'none',
  },
  dragOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(102, 126, 234, 0.1)',
    backdropFilter: 'blur(8px)',
    border: '3px dashed rgba(102, 126, 234, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 200,
    pointerEvents: 'none',
  },
  dragContent: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#667eea',
  },
  header: {
    padding: '20px 24px',
    borderBottom: '1px solid rgba(102, 126, 234, 0.1)',
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  closeButton: {
    background: 'transparent',
    border: 'none',
    color: '#8b92a8',
    fontSize: '20px',
    cursor: 'pointer',
    padding: 0,
    width: '24px',
    height: '24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#e0e6ed',
    flex: 1,
  },
  widthIndicator: {
    fontSize: '11px',
    color: '#6b7785',
    padding: '4px 8px',
    background: 'rgba(102, 126, 234, 0.1)',
    borderRadius: '4px',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: '12px',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '8px',
  },
  emptyTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#e0e6ed',
  },
  emptySubtitle: {
    fontSize: '14px',
    color: '#6b7785',
    textAlign: 'center',
  },
  messageRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-start',
  },
  messageAvatar: {
    fontSize: '24px',
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  messageBlock: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  messageLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#8b92a8',
  },
  messageContent: {
    color: '#e0e6ed',
    fontSize: '14px',
    lineHeight: '1.6',
    whiteSpace: 'pre-wrap',
  },
  filesPreview: {
    padding: '12px 24px',
    borderTop: '1px solid rgba(102, 126, 234, 0.1)',
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  fileChip: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 12px',
    background: 'rgba(102, 126, 234, 0.15)',
    border: '1px solid rgba(102, 126, 234, 0.3)',
    borderRadius: '16px',
    fontSize: '12px',
    color: '#e0e6ed',
  },
  fileSize: {
    color: '#8b92a8',
    fontSize: '11px',
  },
  fileRemove: {
    background: 'transparent',
    border: 'none',
    color: '#8b92a8',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '0 4px',
  },
  inputWrapper: {
    padding: '16px 24px 24px',
    borderTop: '1px solid rgba(102, 126, 234, 0.1)',
  },
  inputBox: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: '8px',
    padding: '12px',
    background: 'rgba(26, 31, 46, 0.5)',
    border: '1px solid rgba(102, 126, 234, 0.3)',
    borderRadius: '12px',
  },
  plusButton: {
    width: '32px',
    height: '32px',
    background: 'transparent',
    border: '1.5px solid rgba(102, 126, 234, 0.4)',
    borderRadius: '6px',
    color: '#667eea',
    fontSize: '20px',
    fontWeight: '400',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    transition: 'all 0.2s',
  },
  input: {
    flex: 1,
    padding: '6px 0',
    background: 'transparent',
    border: 'none',
    color: '#e0e6ed',
    fontSize: '14px',
    resize: 'none',
    fontFamily: 'inherit',
    outline: 'none',
    maxHeight: '200px',
  },
  sendButton: {
    width: '32px',
    height: '32px',
    background: '#667eea',
    border: 'none',
    borderRadius: '6px',
    color: 'white',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    transition: 'all 0.2s',
  },
  inputHint: {
    fontSize: '11px',
    color: '#6b7785',
    marginTop: '8px',
    textAlign: 'center',
  },
};
