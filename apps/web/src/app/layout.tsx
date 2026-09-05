import type { Metadata } from "next";
import { Archivo_Black, IBM_Plex_Sans, IBM_Plex_Mono, Source_Serif_4 } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const displayFont = IBM_Plex_Sans({
  variable: "--font-display-family",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const headingFont = Archivo_Black({
  variable: "--font-heading-family",
  subsets: ["latin"],
  weight: ["400"],
});

const monoFont = IBM_Plex_Mono({
  variable: "--font-mono-family",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const readerFont = Source_Serif_4({
  variable: "--font-reader-family",
  subsets: ["latin"],
  weight: ["400", "600"],
});

export const metadata: Metadata = {
  title: "StoryTrace",
  description: "Narrative continuity intelligence.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${displayFont.variable} ${headingFont.variable} ${monoFont.variable} ${readerFont.variable} h-full antialiased`}
      style={{
        // @ts-expect-error -- custom properties aren't in the CSSProperties type
        "--font-display": "var(--font-display-family), ui-sans-serif, system-ui, sans-serif",
        "--font-heading": "var(--font-heading-family), 'Arial Black', sans-serif",
        "--font-reader": "var(--font-reader-family), Georgia, 'Times New Roman', serif",
        "--font-mono": "var(--font-mono-family), ui-monospace, monospace",
      }}
    >
      <body className="min-h-full">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
