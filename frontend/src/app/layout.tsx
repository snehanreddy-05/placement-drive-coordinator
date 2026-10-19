import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PlacementOS — Placement Drive Coordinator",
  description: "AI-powered enterprise recruitment operations, deterministic eligibility analysis, and cryptographic roster verification.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}>
      <body className="min-h-full flex bg-[#09090B] text-[#F4F4F5]">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}
