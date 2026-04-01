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
          ? '0 12px 60px rgba(0,0,0,0.18), 0 2px 16px rgba(0,0,0,0.1)'
          : '0 2px 16px rgba(0,0,0,0.08)',
        transition: 'border-color 0.35s cubic-bezier(0.2,0,0,1), box-shadow 0.35s cubic-bezier(0.2,0,0,1)',
        overflow: 'hidden',
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
