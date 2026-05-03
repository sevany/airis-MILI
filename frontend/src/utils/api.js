/**
 * API Client for AIRIS Backend
 */

const API_BASE = '/api';

export const api = {
  /**
   * Send chat message with streaming support
   */
  async chat(message, onChunk) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000); // 2 minute timeout

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          stream: true
        }),
        signal: controller.signal
      });

      clearTimeout(timeout);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'chunk') {
                onChunk(data.content);
              } else if (data.type === 'done') {
                return data.full_response;
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      clearTimeout(timeout);
      if (error.name === 'AbortError') {
        throw new Error('Request timeout - response took too long');
      }
      throw error;
    }
  },

  /**
   * Convert text to speech
   */
  async synthesize(text) {
    const response = await fetch(`${API_BASE}/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
      throw new Error(`TTS failed: ${response.status}`);
    }

    const data = await response.json();
    return data.audio_base64;
  },

  /**
   * Get system health
   */
  async health() {
    const response = await fetch(`${API_BASE}/health`);
    return response.json();
  },

  /**
   * Get memory stats
   */
  async memoryStats() {
    const response = await fetch(`${API_BASE}/memory/stats`);
    return response.json();
  }
};