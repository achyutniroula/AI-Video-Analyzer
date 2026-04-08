'use client';

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center cursor-pointer justify-center gap-2 whitespace-nowrap text-sm font-light transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: { default: "", destructive: "", outline: "", secondary: "", ghost: "", link: "" },
      size: { default: "h-9 px-6 py-2", sm: "h-8 px-4 text-xs", lg: "h-10 px-10", icon: "h-9 w-9" },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);
Button.displayName = "Button";

// ─── Glass Button ─────────────────────────────────────────────────────────────

interface GlassButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'default' | 'lg';
}

export const GlassButton = React.forwardRef<HTMLButtonElement, GlassButtonProps>(
  ({ children, className, variant = 'primary', size = 'default', style, ...props }, ref) => {
    const [hovered, setHovered] = React.useState(false);
    const [pressed, setPressed] = React.useState(false);

    const sizeStyles: React.CSSProperties =
      size === 'sm'  ? { padding: '0.5rem 2rem',   fontSize: '0.75rem' } :
      size === 'lg'  ? { padding: '0.875rem 3rem',  fontSize: '0.875rem' } :
                       { padding: '0.75rem 2.5rem', fontSize: '0.82rem' };

    const base: React.CSSProperties =
      variant === 'primary' ? {
        background: hovered ? 'rgba(198,198,200,0.13)' : 'rgba(198,198,200,0.07)',
        border: `1px solid ${hovered ? 'var(--glass-border-h)' : 'rgba(198,198,200,0.2)'}`,
        color: hovered ? 'var(--on-surface)' : 'var(--primary-dim)',
        boxShadow: hovered 
          ? 'inset 0 1px 0 rgba(255,255,255,0.08), 0 0 20px rgba(255, 0, 127, 0.1)' 
          : 'inset 0 0 15px rgba(100, 200, 255, 0.05)',
      } : variant === 'secondary' ? {
        background: hovered ? 'rgba(255,255,255,0.07)' : 'rgba(255,255,255,0.03)',
        border: `1px solid ${hovered ? 'var(--outline)' : 'var(--outline-dim)'}`,
        color: hovered ? 'var(--on-muted)' : 'var(--outline)',
        boxShadow: hovered 
          ? '0 0 15px rgba(0, 255, 200, 0.08)' 
          : 'inset 0 0 10px rgba(100, 200, 255, 0.03)',
      } : {
        background: hovered ? 'rgba(255,255,255,0.04)' : 'transparent',
        border: '1px solid transparent',
        color: hovered ? 'var(--on-muted)' : 'var(--outline)',
        boxShadow: hovered 
          ? '0 0 15px rgba(198, 119, 221, 0.1)' 
          : 'none',
      };

    return (
      <button
        ref={ref}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          borderRadius: '4px',
          fontWeight: 300,
          cursor: 'pointer',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          transition: 'all 0.25s cubic-bezier(0.2,0,0,1)',
          transform: pressed ? 'scale(0.975)' : hovered ? 'scale(1.01)' : 'scale(1)',
          whiteSpace: 'nowrap',
          fontFamily: "'Manrope', sans-serif",
          minWidth: 120,
          backgroundImage: hovered
            ? 'linear-gradient(135deg, rgba(255, 0, 127, 0.06), rgba(0, 255, 200, 0.03), rgba(100, 200, 255, 0.05))'
            : 'linear-gradient(135deg, rgba(255, 0, 127, 0.02), rgba(0, 255, 200, 0.01), rgba(100, 200, 255, 0.02))',
          backgroundBlendMode: 'overlay',
          ...sizeStyles,
          ...base,
          ...style,
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => { setHovered(false); setPressed(false); }}
        onMouseDown={() => setPressed(true)}
        onMouseUp={() => setPressed(false)}
        {...props}
      >
        {children}
      </button>
    );
  }
);
GlassButton.displayName = "GlassButton";

// ─── Liquid Button ────────────────────────────────────────────────────────────

const liquidButtonVariants = cva(
  "inline-flex items-center transition-all justify-center cursor-pointer gap-2 whitespace-nowrap text-sm font-light disabled:pointer-events-none disabled:opacity-40 outline-none",
  {
    variants: {
      variant: { default: "hover:scale-[1.02] duration-300", silver: "hover:scale-[1.02] duration-300" },
      size: { default: "h-11 px-10", sm: "h-9 px-6 text-xs", lg: "h-13 px-12" },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

function GlassFilter() {
  return (
    <svg className="hidden">
      <defs>
        <filter id="container-glass" x="0%" y="0%" width="100%" height="100%" colorInterpolationFilters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency="0.05 0.05" numOctaves={1} seed="1" result="turbulence" />
          <feGaussianBlur in="turbulence" stdDeviation={2} result="blurredNoise" />
          <feDisplacementMap in="SourceGraphic" in2="blurredNoise" scale={55} xChannelSelector="R" yChannelSelector="B" result="displaced" />
          <feGaussianBlur in="displaced" stdDeviation={3} result="finalBlur" />
          <feComposite in="finalBlur" in2="finalBlur" operator="over" />
        </filter>
      </defs>
    </svg>
  );
}

export function LiquidButton({
  className, variant, size, asChild = false, children, ...props
}: React.ComponentProps<"button"> & VariantProps<typeof liquidButtonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return (
    <>
      <Comp
        className={cn("relative rounded-sm", liquidButtonVariants({ variant, size, className }))}
        {...props}
      >
        <div className="absolute top-0 left-0 z-0 h-full w-full rounded-sm
          shadow-[0_0_6px_rgba(0,0,0,0.04),0_2px_6px_rgba(0,0,0,0.1),inset_1px_1px_1px_-0.5px_rgba(255,255,255,0.12),inset_-1px_-1px_1px_-0.5px_rgba(255,255,255,0.06),inset_0_0_4px_4px_rgba(255,255,255,0.03)]
          border border-white/[0.07] bg-white/[0.04]" />
        <div className="absolute top-0 left-0 isolate -z-10 h-full w-full overflow-hidden rounded-sm" style={{ backdropFilter: 'url("#container-glass")' }} />
        <div className="pointer-events-none z-10 relative" style={{ color: 'var(--on-muted)' }}>{children}</div>
        <GlassFilter />
      </Comp>
    </>
  );
}

// ─── Metal Button ─────────────────────────────────────────────────────────────

type ColorVariant = "default" | "primary" | "silver" | "success" | "error";
interface MetalButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ColorVariant;
  wrapperStyle?: React.CSSProperties;
}

const colorVariants: Record<ColorVariant, { outer: string; inner: string; button: string; textColor: string; textShadow: string; hoverShadow: string }> = {
  default: { outer: "bg-gradient-to-b from-[#000] to-[#5a5c5d]", inner: "bg-gradient-to-b from-[#d4d4d6] via-[#3e3f41] to-[#c6c6c8]", button: "bg-gradient-to-b from-[#b8b9bb] to-[#767578]", textColor: "text-[#0e0e0f]", textShadow: "[text-shadow:_0_-1px_0_rgb(80_80_80_/_40%)]", hoverShadow: "rgba(198,198,200,0.2)" },
  silver: { outer: "bg-gradient-to-b from-[#000] to-[#5a5c5d]", inner: "bg-gradient-to-b from-[#d4d4d6] via-[#3e3f41] to-[#c6c6c8]", button: "bg-gradient-to-b from-[#b8b9bb] to-[#767578]", textColor: "text-[#0e0e0f]", textShadow: "[text-shadow:_0_-1px_0_rgb(80_80_80_/_40%)]", hoverShadow: "rgba(198,198,200,0.2)" },
  primary: { outer: "bg-gradient-to-b from-[#000] to-[#5a5c5d]", inner: "bg-gradient-to-b from-[#d4d4d6] via-[#3e3f41] to-[#c6c6c8]", button: "bg-gradient-to-b from-[#c6c6c8] to-[#767578]", textColor: "text-[#0e0e0f]", textShadow: "[text-shadow:_0_-1px_0_rgb(80_80_80_/_40%)]", hoverShadow: "rgba(198,198,200,0.25)" },
  success: { outer: "bg-gradient-to-b from-[#005A43] to-[#7CCB9B]", inner: "bg-gradient-to-b from-[#E5F8F0] via-[#00352F] to-[#D1F0E6]", button: "bg-gradient-to-b from-[#9ADBC8] to-[#3E8F7C]", textColor: "text-white", textShadow: "[text-shadow:_0_-1px_0_rgb(6_78_59_/_100%)]", hoverShadow: "rgba(52,211,153,0.25)" },
  error: { outer: "bg-gradient-to-b from-[#5A0000] to-[#bb5551]", inner: "bg-gradient-to-b from-[#FFDEDE] via-[#680002] to-[#FFE9E9]", button: "bg-gradient-to-b from-[#ee7d77] to-[#A45253]", textColor: "text-white", textShadow: "[text-shadow:_0_-1px_0_rgb(146_64_14_/_100%)]", hoverShadow: "rgba(238,125,119,0.25)" },
};

const ShineEffect = ({ isPressed }: { isPressed: boolean }) => (
  <div className={cn("pointer-events-none absolute inset-0 z-20 overflow-hidden transition-opacity duration-300", isPressed ? "opacity-20" : "opacity-0")}>
    <div className="absolute inset-0 rounded-sm bg-gradient-to-r from-transparent via-neutral-100 to-transparent" />
  </div>
);

export const MetalButton = React.forwardRef<HTMLButtonElement, MetalButtonProps>(
  ({ children, className, variant = "silver", wrapperStyle, ...props }, ref) => {
    const [isPressed, setIsPressed] = React.useState(false);
    const [isHovered, setIsHovered] = React.useState(false);
    const [isTouchDevice, setIsTouchDevice] = React.useState(false);
    React.useEffect(() => { setIsTouchDevice("ontouchstart" in window || navigator.maxTouchPoints > 0); }, []);
    const colors = colorVariants[variant];
    return (
      <div
        className={cn("relative inline-flex transform-gpu rounded-sm p-[1.25px] will-change-transform", colors.outer)}
        style={{
          transform: isPressed ? "translateY(2px) scale(0.99)" : "scale(1)",
          boxShadow: isPressed ? "0 1px 2px rgba(0,0,0,0.2)" : isHovered && !isTouchDevice ? `0 4px 24px ${colors.hoverShadow}` : "0 3px 10px rgba(0,0,0,0.3)",
          transition: "all 250ms cubic-bezier(0.2,0,0,1)",
          ...wrapperStyle,
        }}
      >
        <div className={cn("absolute inset-[1px] transform-gpu rounded-sm will-change-transform", colors.inner)} style={{ filter: isHovered && !isPressed && !isTouchDevice ? "brightness(1.04)" : "none" }} />
        <button
          ref={ref}
          className={cn("relative z-10 m-[1px] rounded-sm inline-flex h-11 transform-gpu cursor-pointer items-center justify-center overflow-hidden px-10 text-xs leading-none font-light tracking-widest uppercase will-change-transform outline-none", colors.button, colors.textColor, colors.textShadow, className)}
          style={{ transform: isPressed ? "scale(0.97)" : "scale(1)", transition: "all 250ms cubic-bezier(0.2,0,0,1)", fontFamily: "'Manrope', sans-serif", letterSpacing: '0.12em' }}
          {...props}
          onMouseDown={() => setIsPressed(true)}
          onMouseUp={() => setIsPressed(false)}
          onMouseLeave={() => { setIsPressed(false); setIsHovered(false); }}
          onMouseEnter={() => { if (!isTouchDevice) setIsHovered(true); }}
          onTouchStart={() => setIsPressed(true)}
          onTouchEnd={() => setIsPressed(false)}
          onTouchCancel={() => setIsPressed(false)}
        >
          <ShineEffect isPressed={isPressed} />
          {children || "Button"}
          {isHovered && !isPressed && !isTouchDevice && <div className="pointer-events-none absolute inset-0 bg-gradient-to-t rounded-sm from-transparent to-white/[0.04]" />}
        </button>
      </div>
    );
  }
);
MetalButton.displayName = "MetalButton";

export { Button, buttonVariants };
