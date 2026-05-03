export default function VoiceButton({ status, onClick }) {
  const getButtonStyle = () => {
    const base = {
      position: 'absolute',
      bottom: '80px',
      left: '50%',
      transform: 'translateX(-50%)',
      width: '80px',
      height: '80px',
      borderRadius: '50%',
      border: 'none',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '32px',
      transition: 'all 0.3s ease',
      zIndex: 10,
    };

    if (status === 'listening') {
      return {
        ...base,
        background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
        boxShadow: '0 0 40px rgba(16, 185, 129, 0.6)',
      };
    }

    if (status === 'speaking') {
      return {
        ...base,
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        boxShadow: '0 0 40px rgba(102, 126, 234, 0.6)',
        animation: 'pulse 1.5s infinite',
      };
    }

    return {
      ...base,
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      boxShadow: '0 0 20px rgba(102, 126, 234, 0.3)',
    };
  };

  return (
    <>
      <style>
        {`
          @keyframes pulse {
            0%, 100% {
              transform: translateX(-50%) scale(1);
            }
            50% {
              transform: translateX(-50%) scale(1.1);
            }
          }
        `}
      </style>
      <button
        style={getButtonStyle()}
        onClick={onClick}
        disabled={status === 'speaking'}
      >
        {status === 'listening' ? '⏸' : '🎤'}
      </button>
    </>
  );
}
