"""
Whisper Speech-to-Text Module
Converts audio to text using Faster-Whisper (more stable than openai-whisper)
"""
from faster_whisper import WhisperModel
import os
import subprocess
import tempfile
import time

class STTEngine:
    """Faster-Whisper STT wrapper for voice input"""
    
    def __init__(self, model_size="base"):
        """
        Initialize Faster-Whisper model
        
        Args:
            model_size: tiny, base, small, medium, large-v2, large-v3
                       base = good balance
        """
        print(f"🎤 Loading Faster-Whisper model ({model_size})...")
        # Use CPU with int8 for better compatibility
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print(f"✓ Faster-Whisper ready")
    
    def transcribe(self, audio_data, language=None):
        """
        Transcribe audio to text
        
        Args:
            audio_data: Audio bytes (WAV, MP3, WebM, etc)
            language: Optional language code ('en', 'ms', etc)
            
        Returns:
            dict: {
                'text': transcribed text,
                'language': detected language,
                'confidence': confidence score
            }
        """
        print(f"🎤 Transcribing audio ({len(audio_data)} bytes)...")
        
        # Save to debug folder to inspect
        debug_dir = "backend/data/audio_debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        try:
            # Save incoming audio to temp file
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp_input:
                tmp_input.write(audio_data)
                input_path = tmp_input.name
            
            # Also save a copy for debugging
            timestamp = int(time.time())
            debug_webm = f"{debug_dir}/debug_{timestamp}.webm"
            with open(debug_webm, 'wb') as f:
                f.write(audio_data)
            print(f"📁 Debug copy saved: {debug_webm}")
            
            # Convert to WAV using ffmpeg
            output_path = input_path.replace('.webm', '.wav')
            debug_wav = f"{debug_dir}/debug_{timestamp}.wav"
            
            try:
                print(f"🔄 Converting WebM → WAV...")
                
                # Use ffmpeg to convert WebM to WAV (16kHz mono)
                result = subprocess.run([
                    'ffmpeg', '-i', input_path,
                    '-ar', '16000',  # 16kHz sample rate
                    '-ac', '1',      # Mono
                    '-y',            # Overwrite
                    output_path
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"❌ ffmpeg error: {result.stderr}")
                    raise Exception(f"ffmpeg conversion failed: {result.stderr}")
                
                print(f"✓ Converted to WAV")
                
                # Save WAV for debugging
                import shutil
                shutil.copy(output_path, debug_wav)
                print(f"📁 Debug WAV saved: {debug_wav}")
                
                # Check WAV file size
                wav_size = os.path.getsize(output_path)
                print(f"📊 WAV file size: {wav_size} bytes")
                
                if wav_size == 0:
                    raise Exception("WAV file is empty after conversion")
                
                # Transcribe WAV file with Faster-Whisper
                print(f"🧠 Running Faster-Whisper transcription...")
                
                segments, info = self.model.transcribe(
                    output_path,
                    language=language,
                    beam_size=5
                )
                
                # Collect all segments
                transcribed_text = " ".join([segment.text for segment in segments]).strip()
                
                print(f"✓ Transcribed: '{transcribed_text}'")
                print(f"✓ Detected language: {info.language} (probability: {info.language_probability:.2f})")
                
                return {
                    'text': transcribed_text,
                    'language': info.language,
                    'confidence': info.language_probability
                }
            
            finally:
                # Clean up temp files (but keep debug copies)
                if os.path.exists(input_path):
                    os.unlink(input_path)
                    print(f"🗑️  Cleaned up: {input_path}")
                if os.path.exists(output_path):
                    os.unlink(output_path)
                    print(f"🗑️  Cleaned up: {output_path}")
        
        except Exception as e:
            print(f"❌ STT error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def health_check(self):
        """Check if STT is working"""
        try:
            if self.model:
                return True, "✓ Faster-Whisper ready"
        except Exception as e:
            return False, f"✗ Whisper error: {str(e)}"