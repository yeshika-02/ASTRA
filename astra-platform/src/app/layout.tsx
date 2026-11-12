import type { Metadata } from 'next';
import { IBM_Plex_Mono, Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { GlobalClientContainer } from '@/components/layout/GlobalClientContainer';

const inter = Inter({ subsets: ['latin'] });
// Self-hosted at build time by next/font (no runtime request to Google Fonts).
const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-plex-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'ASTRA — Stellar Intelligence Platform',
  description:
    'Automated Stellar Transient Recognition & Analysis. A scientific ML platform for TESS photometric variability classification.',
  keywords: ['astronomy', 'machine learning', 'stellar classification', 'TESS', 'photometry'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${plexMono.variable}`}>
      <body className={inter.className} style={{ background: '#05070B' }}>
        <Providers>
          <GlobalClientContainer>{children}</GlobalClientContainer>
        </Providers>
      </body>
    </html>
  );
}
