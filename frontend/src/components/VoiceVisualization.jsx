import { useEffect, useRef } from 'react';

export default function VoiceVisualization({ status }) {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    let particles = [];
    let connections = [];
    let time = 0;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const baseRadius = Math.min(canvas.width, canvas.height) * 0.35; // Increased from 0.2 to 0.35

    // Create particles in 3D sphere
    const createParticles = () => {
      particles = [];
      const count = 250; // Increased from 150 for denser globe
      
      for (let i = 0; i < count; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const r = baseRadius + (Math.random() - 0.5) * 20;
        
        particles.push({
          theta,
          phi,
          r,
          baseR: r,
          speed: 0.001 + Math.random() * 0.002,
          size: Math.random() * 2 + 1,
        });
      }
    };

    createParticles();

    const draw3DParticle = (particle, pulse) => {
      const r = particle.r + pulse;
      const x = centerX + r * Math.sin(particle.phi) * Math.cos(particle.theta);
      const y = centerY + r * Math.sin(particle.phi) * Math.sin(particle.theta);
      const z = r * Math.cos(particle.phi);
      
      // Size based on Z depth
      const scale = 1 + z / (baseRadius * 2);
      const size = particle.size * scale;
      const opacity = 0.3 + (scale - 0.5) * 0.7;
      
      return { x, y, size, opacity, z };
    };

    const drawGlobe = () => {
      // Clear with fade effect
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Pulsing effect
      const pulse = status === 'speaking' ? 
        Math.sin(time * 0.05) * 15 : 
        status === 'listening' ? 
        Math.sin(time * 0.1) * 8 : 
        Math.sin(time * 0.02) * 3;

      // Rotate particles
      particles.forEach(p => {
        p.theta += p.speed;
      });

      // Draw connections first (behind particles)
      ctx.strokeStyle = 'rgba(102, 126, 234, 0.1)';
      ctx.lineWidth = 0.5;
      
      const positions = particles.map(p => draw3DParticle(p, pulse));
      
      for (let i = 0; i < positions.length; i++) {
        for (let j = i + 1; j < positions.length; j++) {
          const dx = positions[i].x - positions[j].x;
          const dy = positions[i].y - positions[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 80) {
            const opacity = (1 - dist / 80) * 0.2;
            ctx.strokeStyle = `rgba(102, 126, 234, ${opacity})`;
            ctx.beginPath();
            ctx.moveTo(positions[i].x, positions[i].y);
            ctx.lineTo(positions[j].x, positions[j].y);
            ctx.stroke();
          }
        }
      }

      // Draw outer glow rings
      for (let i = 0; i < 3; i++) {
        const ringRadius = baseRadius + pulse + (i * 30);
        const ringOpacity = 0.1 - (i * 0.03);
        
        ctx.strokeStyle = `rgba(102, 126, 234, ${ringOpacity})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(centerX, centerY, ringRadius, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Draw particles (sorted by Z for proper layering)
      positions.sort((a, b) => a.z - b.z);
      
      positions.forEach(pos => {
        // Glow effect
        const gradient = ctx.createRadialGradient(
          pos.x, pos.y, 0,
          pos.x, pos.y, pos.size * 3
        );
        gradient.addColorStop(0, `rgba(102, 126, 234, ${pos.opacity})`);
        gradient.addColorStop(1, 'rgba(102, 126, 234, 0)');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, pos.size * 3, 0, Math.PI * 2);
        ctx.fill();
        
        // Core particle
        ctx.fillStyle = `rgba(255, 255, 255, ${pos.opacity * 0.8})`;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, pos.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Center glow
      const centerGradient = ctx.createRadialGradient(
        centerX, centerY, 0,
        centerX, centerY, baseRadius + pulse
      );
      centerGradient.addColorStop(0, 'rgba(102, 126, 234, 0.05)');
      centerGradient.addColorStop(0.5, 'rgba(102, 126, 234, 0.02)');
      centerGradient.addColorStop(1, 'rgba(102, 126, 234, 0)');
      
      ctx.fillStyle = centerGradient;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius + pulse, 0, Math.PI * 2);
      ctx.fill();

      time++;
    };

    const animate = () => {
      drawGlobe();
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      createParticles();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      window.removeEventListener('resize', handleResize);
    };
  }, [status]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
      }}
    />
  );
}
