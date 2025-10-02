

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Providers from '../components/Providers';
import ErrorBoundary from '../components/ErrorBoundary';
import Script from "next/script";
import Header from '../components/Header';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "French Novel Tool",
  description: "Process French novels and export to Google Sheets",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Scripts are loaded asynchronously using Next.js Script component */}
        <Script src="https://apis.google.com/js/api.js" strategy="afterInteractive" />
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
      </head>
      <body className={inter.className}>
        <ErrorBoundary>
          <Providers>
            <Header />
            {children}
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
