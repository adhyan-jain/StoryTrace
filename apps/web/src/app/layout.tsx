import type { Metadata } from "next";
import { Fraunces, Source_Serif_4, IBM_Plex_Mono, Inter } from "next/font/google";
import "./globals.css";

// A manuscript/forensic-annotation identity: a characterful display serif for
// the wordmark and chapter headings, a comfortable reading serif for the
// prose itself, a UI sans for chrome, and a mono face for the analytical
// bits (page numbers, sequence numbers, confidence scores) that gives the
// continuity-autopsy findings a "case file" register.
const displaySerif = Fraunces({
  variable: "--font-display",
  subsets: ["latin"],
  axes: ["opsz", "SOFT", "WONK"],
  weight: ["400", "600"],
});

const readingSerif = Source_Serif_4({
  variable: "--font-reading",
  subsets: ["latin"],
});

const uiSans = Inter({
  variable: "--font-ui",
  subsets: ["latin"],
});

const dataMono = IBM_Plex_Mono({
  variable: "--font-data",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "StoryTrace — Continuity Autopsy",
  description: "A document-agnostic continuity engine for screenplays and novels.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${displaySerif.variable} ${readingSerif.variable} ${uiSans.variable} ${dataMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
