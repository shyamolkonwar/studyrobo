import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50`}
      >
        <div className="flex h-screen">
          {/* Sidebar */}
          <div className="w-64 bg-white shadow-lg">
            <div className="p-6">
              <h1 className="text-2xl font-bold text-gray-800">StudyRobo</h1>
            </div>
            <nav className="mt-6">
              <a href="/" className="block px-6 py-3 text-gray-700 hover:bg-gray-100 hover:text-gray-900">
                💬 Chat
              </a>
              <a href="/" className="block px-6 py-3 text-gray-700 hover:bg-gray-100 hover:text-gray-900">
                📧 Emails
              </a>
              <a href="/" className="block px-6 py-3 text-gray-700 hover:bg-gray-100 hover:text-gray-900">
                📚 Attendance
              </a>
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
