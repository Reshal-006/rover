import React, { useEffect, useRef } from 'react';

export const LandingCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Mouse interactivity
    const mouse = { x: -1000, y: -1000, radius: 250 };
    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    const handleMouseLeave = () => {
      mouse.x = -1000;
      mouse.y = -1000;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    let isLightMode = document.documentElement.classList.contains('light');
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          isLightMode = document.documentElement.classList.contains('light');
        }
      });
    });
    observer.observe(document.documentElement, { attributes: true });

    class Particle {
      x: number;
      y: number;
      vx: number;
      vy: number;
      radius: number;
      baseX: number;
      baseY: number;
      density: number;

      constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.baseX = this.x;
        this.baseY = this.y;
        this.density = (Math.random() * 30) + 1;
        this.radius = Math.random() * 2 + 1;
        this.vx = (Math.random() - 0.5) * 0.8;
        this.vy = (Math.random() - 0.5) * 0.8;
      }

      update() {
        // Natural movement
        this.x += this.vx;
        this.y += this.vy;

        // Bounce off walls softly
        if (this.x < 0 || this.x > width) this.vx *= -1;
        if (this.y < 0 || this.y > height) this.vy *= -1;

        // Mouse interaction (Magnetic repel/attract)
        const dx = mouse.x - this.x;
        const dy = mouse.y - this.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < mouse.radius) {
          // Push particles away gently but connect them visually later
          const forceDirectionX = dx / distance;
          const forceDirectionY = dy / distance;
          const maxDistance = mouse.radius;
          const force = (maxDistance - distance) / maxDistance;
          const directionX = forceDirectionX * force * this.density * 0.05;
          const directionY = forceDirectionY * force * this.density * 0.05;
          
          this.x -= directionX;
          this.y -= directionY;
        }
      }

      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = isLightMode ? 'rgba(2, 132, 199, 0.6)' : 'rgba(56, 189, 248, 0.8)';
        ctx.fill();
      }
    }

    const particles: Particle[] = [];
    // Calculate optimal particle count based on screen size
    const particleCount = Math.min(200, Math.floor((width * height) / 8000));
    
    for (let i = 0; i < particleCount; i++) {
      particles.push(new Particle());
    }

    const connectParticles = () => {
      const maxDistance = 150;
      for (let a = 0; a < particles.length; a++) {
        for (let b = a + 1; b < particles.length; b++) {
          const dx = particles[a].x - particles[b].x;
          const dy = particles[a].y - particles[b].y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < maxDistance) {
            const opacity = 1 - (distance / maxDistance);
            ctx.beginPath();
            ctx.moveTo(particles[a].x, particles[a].y);
            ctx.lineTo(particles[b].x, particles[b].y);
            ctx.lineWidth = isLightMode ? 1 : 1.5;
            ctx.strokeStyle = isLightMode 
              ? `rgba(2, 132, 199, ${opacity * 0.3})`
              : `rgba(56, 189, 248, ${opacity * 0.3})`;
            ctx.stroke();
          }
        }

        // Connect to mouse with a special glowing line
        const mdx = mouse.x - particles[a].x;
        const mdy = mouse.y - particles[a].y;
        const mDistance = Math.sqrt(mdx * mdx + mdy * mdy);
        
        if (mDistance < mouse.radius * 0.8) {
          const mOpacity = 1 - (mDistance / (mouse.radius * 0.8));
          ctx.beginPath();
          ctx.moveTo(particles[a].x, particles[a].y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.lineWidth = 1.5;
          ctx.strokeStyle = isLightMode 
            ? `rgba(14, 165, 233, ${mOpacity * 0.6})`
            : `rgba(56, 189, 248, ${mOpacity * 0.8})`;
          ctx.stroke();
        }
      }
    };

    const render = () => {
      // Background gradient
      const bgColor = isLightMode ? '#f8fafc' : '#020617';
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, width, height);

      // Subtle center/mouse glow
      const glowX = mouse.x !== -1000 ? mouse.x : width / 2;
      const glowY = mouse.y !== -1000 ? mouse.y : height / 2;
      const gradient = ctx.createRadialGradient(glowX, glowY, 0, glowX, glowY, width * 0.6);
      gradient.addColorStop(0, isLightMode ? 'rgba(2, 132, 199, 0.05)' : 'rgba(56, 189, 248, 0.05)');
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Draw and update particles
      ctx.globalCompositeOperation = isLightMode ? 'multiply' : 'screen';
      
      for (let i = 0; i < particles.length; i++) {
        particles[i].update();
        particles[i].draw();
      }
      connectParticles();

      ctx.globalCompositeOperation = 'source-over';
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      observer.disconnect();
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none z-0 transition-opacity duration-1000"
    />
  );
};

