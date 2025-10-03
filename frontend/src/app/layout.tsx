
import type { Metadata } from "next";
import { Inter, Libre_Baskerville } from 'next/font/google';
import "./globals.css";
import Providers from '../components/Providers';
import ErrorBoundary from '../components/ErrorBoundary';
import Script from "next/script";
import Header from '../components/Header';
import ConnectionStatusBanner from '../components/ConnectionStatusBanner';
import SkipLink from '../components/SkipLink';

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-inter',
  display: 'swap',
});

const libreBaskerville = Libre_Baskerville({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-libre-baskerville',
  display: 'swap',
});

export const metadata: Metadata = {
  title: "French Novel Tool",
  description: "Process French novels and export to Google Sheets",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${libreBaskerville.variable}`}>
      <head>
        {/* Scripts are loaded asynchronously using Next.js Script component */}
        <Script src="https://apis.google.com/js/api.js" strategy="afterInteractive" />
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
      </head>
      <body className={inter.className}>
        <ErrorBoundary>
          <Providers>
            <SkipLink />
            <Header />
            <ConnectionStatusBanner />
            <main id="main-content" role="main">
              {children}
            </main>
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
