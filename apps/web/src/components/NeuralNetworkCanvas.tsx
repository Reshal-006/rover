import React, { useEffect, useRef } from 'react';

export const NeuralNetworkCanvas: React.FC = () => {
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

    const spacing = 45; // Reduced density for much better performance
    let time = 0;

    let isLightMode = !document.documentElement.classList.contains('dark');

    // Watch for theme changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          isLightMode = !document.documentElement.classList.contains('dark');
        }
      });
    });
    observer.observe(document.documentElement, { attributes: true });

    const render = () => {
      time += 0.02;

      // Theme-based colors (Warm off-white for light mode to reduce glare)
      const bgColor = isLightMode ? '#f5f5f4' : '#010309'; // stone-100 for a textured warm feel
      const centerGlow = isLightMode ? 'rgba(217, 119, 6, 0.03)' : 'rgba(6, 182, 212, 0.03)'; // Warm amber glow in light mode

      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, width, height);

      // Add a very subtle gradient vignette
      const gradient = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width * 0.8);
      gradient.addColorStop(0, centerGlow);
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Use multiply in light mode for darker dots, screen in dark mode for glowing dots
      ctx.globalCompositeOperation = isLightMode ? 'multiply' : 'screen';

      const cols = Math.floor(width / spacing) + 2;
      const rows = Math.floor(height / spacing) + 2;

      for (let i = 0; i < cols; i++) {
        for (let j = 0; j < rows; j++) {
          const x = i * spacing;
          const y = j * spacing;

          // Mouse distance
          const dx = mouse.x - x;
          const dy = mouse.y - y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          // Magnetic ripple effect
          const isHovered = dist < mouse.radius;
          let hoverForce = 0;
          if (isHovered) {
            hoverForce = Math.pow(1 - (dist / mouse.radius), 2);
          }

          // Ambient idle animation
          const ambient = Math.sin(i * 0.1 + j * 0.1 + time) * 0.5 + 0.5;

          // Dot size and opacity based on hover and ambient
          const size = 1 + (hoverForce * 2.5);

          // In light mode, dots are darker (slate-800 or cyan-600)
          const baseOpacity = isLightMode ? (0.05 + ambient * 0.05) : (0.03 + ambient * 0.03);
          const finalOpacity = Math.min(1, baseOpacity + (hoverForce * 0.5));

          ctx.beginPath();
          ctx.arc(x, y, size, 0, Math.PI * 2);

          if (isHovered && hoverForce > 0.3) {
            const activeColor = isLightMode ? `rgba(2, 132, 199, ${finalOpacity})` : `rgba(56, 189, 248, ${finalOpacity})`;
            ctx.fillStyle = activeColor;
            // shadowBlur removed for massive performance gains
          } else {
            const idleColor = isLightMode ? `rgba(100, 116, 139, ${finalOpacity})` : `rgba(148, 163, 184, ${finalOpacity})`;
            ctx.fillStyle = idleColor;
          }

          ctx.fill();
        }
      }

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
      className="fixed inset-0 w-full h-full pointer-events-none z-0"
    />
  );
};
