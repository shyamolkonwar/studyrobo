import type { Metadata } from "next";
import { Inter, Figtree, Geist_Mono } from "next/font/google";
import "./globals.css";
import AuthListener from "@/components/auth-listener";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const figtree = Figtree({
  variable: "--font-figtree",
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Lemma",
  description: "Your personal AI academic mentor",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${figtree.variable} ${geistMono.variable} antialiased`}
      >
        <AuthListener />
        <div className="min-h-screen bg-background">
          {children}
        </div>
      </body>
    </html>
  );
}
