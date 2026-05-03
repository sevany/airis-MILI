"""
ElevenLabs Text-to-Speech Module
Converts AIRIS responses to speech using ElevenLabs API
"""
from elevenlabs import generate, set_api_key, Voice, VoiceSettings
from backend.config import Config
import base64

# Set API key from config
if Config.ELEVENLABS_API_KEY:
    set_api_key(Config.ELEVENLABS_API_KEY)

class TTSEngine:
    """ElevenLabs TTS wrapper for AIRIS voice"""
    
    def __init__(self, voice_id=None, api_key=None):
        self.voice_id = voice_id or Config.ELEVENLABS_VOICE_ID
        if api_key:
            set_api_key(api_key)
    
    def synthesize(self, text):
        """
        Convert text to speech with advanced voice settings
        
        Args:
            text: String to convert to speech
            
        Returns:
            Audio bytes (MP3 format)
        """
        try:
            # Advanced voice settings for human-like speech
            audio = generate(
                text=text,
                voice=Voice(
                    voice_id=self.voice_id,
                    settings=VoiceSettings(
                        stability=0.4,           # More expressive, emotional (M3GAN!)
                        similarity_boost=0.8,    # Voice consistency
                        style=0.6,              # Natural tone variations
                        use_speaker_boost=True   # Clear, crisp speech
                    )
                ),
                model="eleven_turbo_v2_5"  # Faster, more natural model
            )
            
            return audio
            
        except Exception as e:
            print(f"❌ TTS error: {str(e)}")
            raise
    
    def synthesize_base64(self, text):
        """
        Convert text to speech and return as base64-encoded string
        
        Args:
            text: String to convert to speech
            
        Returns:
            Base64-encoded audio string
        """
        audio_bytes = self.synthesize(text)
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    def health_check(self):
        """Check if TTS is configured and working"""
        if not Config.ELEVENLABS_API_KEY:
            return False, "✗ ElevenLabs API key not configured"
        if not self.voice_id:
            return False, "✗ Voice ID not configured"
        
        try:
            # Test synthesis with short text
            test_audio = self.synthesize("Test")
            if test_audio:
                return True, f"✓ TTS ready (voice: {self.voice_id[:8]}...)"
        except Exception as e:
            return False, f"✗ TTS test failed: {str(e)}"