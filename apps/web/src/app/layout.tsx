import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const displayFont = Inter({
  variable: "--font-display-family",
  subsets: ["latin"],
});

const monoFont = JetBrains_Mono({
  variable: "--font-mono-family",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "StoryTrace",
  description: "Narrative continuity intelligence.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${displayFont.variable} ${monoFont.variable} h-full antialiased`}
      style={{
        // Georgia is a system font, no next/font loading needed for it.
        // @ts-expect-error -- custom properties aren't in the CSSProperties type
        "--font-display": "var(--font-display-family), ui-sans-serif, system-ui, sans-serif",
        "--font-reader": "Georgia, 'Times New Roman', serif",
        "--font-mono": "var(--font-mono-family), ui-monospace, monospace",
      }}
    >
      <body className="min-h-full">{children}</body>
    </html>
  );
}
