import type { Metadata } from "next";
import { Nunito, DM_Sans } from "next/font/google";
import "./globals.css";

const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
});

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "Repox — Understand Any Codebase Instantly",
  description:
    "Upload your repository ZIP and get a personalized, visual explanation of the codebase — no technical background required.",
  keywords: ["repository", "codebase", "explanation", "non-technical", "code tour"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${dmSans.variable} ${nunito.variable} font-sans antialiased min-h-screen relative`}>
        {/* Floating 3D Blobs (Background) */}
        <div className="pointer-events-none fixed inset-0 overflow-hidden -z-10">
          <div className="absolute h-[60vh] w-[60vh] rounded-full blur-3xl bg-[#8B5CF6]/8 -top-[10%] -left-[10%] animate-clay-float" />
          <div className="absolute h-[60vh] w-[60vh] rounded-full blur-3xl bg-[#EC4899]/8 -right-[10%] top-[20%] animate-clay-float-delayed" />
          <div className="absolute h-[50vh] w-[50vh] rounded-full blur-3xl bg-[#0EA5E9]/8 bottom-[10%] left-[20%] animate-clay-float-slow" />
        </div>
        {children}
      </body>
    </html>
  );
}
