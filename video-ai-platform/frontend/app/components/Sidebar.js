'use client';

import { usePathname, useRouter } from 'next/navigation';
import { signOut } from 'aws-amplify/auth';
import { useTheme } from '../../lib/ThemeContext';

const font = "'Manrope', sans-serif";

const navItems = [
  { label: 'Dashboard', icon: 'dashboard', href: '/dashboard' },
  { label: 'My Videos', icon: 'video_library', href: '/videos' },
  { label: 'Upload', icon: 'upload', href: '/upload' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  const handleSignOut = async () => {
    try { await signOut(); router.push('/'); } catch {}
  };

  return (
    <aside style={{
      position: 'fixed',
      left: 0, top: 0,
      width: 256,
      height: '100vh',
      background: 'var(--surface-low)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      borderRight: '1px solid var(--outline-faint)',
      display: 'flex',
      flexDirection: 'column',
      padding: '2rem 1rem',
      zIndex: 50,
      fontFamily: font,
    }}>

      {/* VisionFlow logo */}
      <div style={{ marginBottom: '3rem', padding: '0 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{
          width: 32, height: 32,
          background: 'linear-gradient(135deg, var(--primary), var(--outline))',
          borderRadius: 4,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 17, color: 'var(--bg)', fontVariationSettings: "'FILL' 1, 'wght' 500" }}>lens</span>
        </div>
        <div>
          <p style={{ fontSize: '1rem', fontWeight: 200, letterSpacing: '0.15em', color: 'var(--on-surface)', lineHeight: 1.2 }}>VisionFlow</p>
          <p style={{ fontSize: '0.6rem', fontWeight: 300, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--outline)', marginTop: 2 }}>Video AI</p>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '2px' }}>
        {navItems.map(item => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
          return (
            <a
              key={item.href}
              href={item.href}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem',
                padding: '0.75rem 1rem', borderRadius: 6,
                background: isActive ? 'var(--glass-bg)' : 'transparent',
                border: isActive ? '1px solid var(--glass-border)' : '1px solid transparent',
                color: isActive ? 'var(--on-surface)' : 'var(--outline)',
                fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.03em',
                transition: 'all 0.2s cubic-bezier(0.2,0,0,1)',
                textDecoration: 'none',
              }}
              onMouseEnter={e => {
                if (!isActive) {
                  e.currentTarget.style.color = 'var(--on-muted)';
                  e.currentTarget.style.background = 'var(--glass-bg)';
                }
              }}
              onMouseLeave={e => {
                if (!isActive) {
                  e.currentTarget.style.color = 'var(--outline)';
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 20, flexShrink: 0 }}>{item.icon}</span>
              <span>{item.label}</span>
            </a>
          );
        })}
      </nav>

      {/* Bottom actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.75rem',
            padding: '0.75rem 1rem',
            background: 'none', border: 'none',
            cursor: 'pointer',
            color: 'var(--outline)',
            fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.03em',
            fontFamily: font, borderRadius: 6,
            transition: 'all 0.2s cubic-bezier(0.2,0,0,1)',
            width: '100%', textAlign: 'left',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--on-muted)'; e.currentTarget.style.background = 'var(--glass-bg)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--outline)'; e.currentTarget.style.background = 'transparent'; }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 20, flexShrink: 0 }}>{theme === 'dark' ? 'light_mode' : 'dark_mode'}</span>
          <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
        </button>

        {/* Sign out */}
        <button
          onClick={handleSignOut}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.75rem',
            padding: '0.75rem 1rem',
            background: 'none', border: 'none',
            cursor: 'pointer',
            color: 'var(--outline)',
            fontSize: '0.875rem', fontWeight: 300, letterSpacing: '0.03em',
            fontFamily: font, borderRadius: 6,
            transition: 'all 0.2s cubic-bezier(0.2,0,0,1)',
            width: '100%', textAlign: 'left',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--on-muted)'; e.currentTarget.style.background = 'var(--glass-bg)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--outline)'; e.currentTarget.style.background = 'transparent'; }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 20, flexShrink: 0 }}>logout</span>
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
