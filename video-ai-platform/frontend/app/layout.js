import './globals.css';
import { AmplifyProvider } from '../lib/AmplifyProvider';
import { ThemeProvider } from '../lib/ThemeContext';

export const metadata = {
  title: 'Video Understanding Platform',
  description: 'AI-powered video understanding and analysis',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@200;300;400;500&display=swap" rel="stylesheet" />
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
      </head>
      <body>
        <ThemeProvider>
          <AmplifyProvider>
            {children}
          </AmplifyProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
