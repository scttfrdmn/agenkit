import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Agenkit on Vercel Edge',
  description: 'Edge-native AI agents with global distribution',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
