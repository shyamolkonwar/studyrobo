import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "StudyRobo",
  description: "AI-powered study assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <div className="flex h-screen bg-background">
          {/* Sidebar */}
          <div className="w-64 bg-card border-r border-border">
            <div className="p-6">
              <h1 className="text-2xl font-bold text-foreground">StudyRobo</h1>
              <p className="text-sm text-muted-foreground mt-1">AI Study Assistant</p>
            </div>
            <nav className="mt-6 px-3">
              <Button variant="ghost" className="w-full justify-start mb-2" asChild>
                <a href="/">
                  💬 Chat
                </a>
              </Button>
              <Button variant="ghost" className="w-full justify-start mb-2" asChild>
                <a href="/">
                  📧 Emails
                </a>
              </Button>
              <Button variant="ghost" className="w-full justify-start mb-2" asChild>
                <a href="/">
                  📚 Attendance
                </a>
              </Button>
            </nav>
          </div>
          {/* Main content */}
          <div className="flex-1 flex flex-col">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
