
import type { Metadata } from "next";
import "./globals.css";
import Providers from '../components/Providers';
import ErrorBoundary from '../components/ErrorBoundary';
import Script from "next/script";
import Header from '../components/Header';
import ConnectionStatusBanner from '../components/ConnectionStatusBanner';
import SkipLink from '../components/SkipLink';

export const metadata: Metadata = {
  title: "French Novel Tool",
  description: "Process French novels and export to Google Sheets",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Google Fonts - loaded at runtime */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
        {/* Scripts are loaded asynchronously using Next.js Script component */}
        <Script src="https://apis.google.com/js/api.js" strategy="afterInteractive" />
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
      </head>
      <body>
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
