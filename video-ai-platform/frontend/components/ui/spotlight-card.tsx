'use client';

import React, { useState, useRef, ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface GlowCardProps {
  children: ReactNode;
  className?: string;
  glowColor?: string;
  onClick?: () => void;
  style?: React.CSSProperties;
  onMouseEnter?: (e: React.MouseEvent<HTMLDivElement>) => void;
  onMouseLeave?: (e: React.MouseEvent<HTMLDivElement>) => void;
}

export const GlowCard: React.FC<GlowCardProps> = ({
  children,
  className = '',
  onClick,
  style,
  onMouseEnter,
  onMouseLeave,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [hovered, setHovered] = useState(false);

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleMouseEnter = (e: React.MouseEvent<HTMLDivElement>) => {
    setHovered(true);
    onMouseEnter?.(e);
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    setHovered(false);
    onMouseLeave?.(e);
  };

  return (
    <div
      ref={cardRef}
      onClick={onClick}
      onPointerMove={handlePointerMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{
        position: 'relative',
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        border: hovered
          ? '1px solid var(--glass-border-h)'
          : '1px solid var(--glass-border)',
        borderRadius: 10,
        boxShadow: hovered
          ? '0 12px 60px rgba(0,0,0,0.18), 0 2px 16px rgba(0,0,0,0.1), inset 0 0 30px rgba(198, 119, 221, 0.08)'
          : '0 2px 16px rgba(0,0,0,0.08), inset 0 0 20px rgba(118, 184, 255, 0.03)',
        transition: 'border-color 0.35s cubic-bezier(0.2,0,0,1), box-shadow 0.35s cubic-bezier(0.2,0,0,1)',
        overflow: 'hidden',
        backgroundImage: hovered
          ? 'linear-gradient(var(--glass-bg), var(--glass-bg)), linear-gradient(135deg, rgba(255, 0, 127, 0.08), rgba(0, 255, 200, 0.04), rgba(100, 200, 255, 0.06))'
          : 'linear-gradient(var(--glass-bg), var(--glass-bg)), linear-gradient(135deg, rgba(255, 0, 127, 0.04), rgba(0, 255, 200, 0.02), rgba(100, 200, 255, 0.03))',
        backgroundClip: 'padding-box, border-box',
        backgroundOrigin: 'border-box',
        ...style,
      }}
      className={cn(className)}
    >
      {hovered && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            pointerEvents: 'none',
            background: `radial-gradient(320px circle at ${mousePos.x}px ${mousePos.y}px, var(--ambient-glow, rgba(198,198,200,0.025)), transparent 70%)`,
            borderRadius: 'inherit',
            zIndex: 0,
          }}
        />
      )}
      <div style={{ position: 'relative', zIndex: 1 }}>
        {children}
      </div>
    </div>
  );
};
