import type { Metadata } from "next";
import { Geist, Geist_Mono, Outfit, Space_Grotesk } from "next/font/google";
import "../index.css";
import Providers from "@/components/providers";
// import Header from "@/components/header";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Sentinel",
  description: " A lightweight GitHub App that gives open source maintainers actionable community intelligence. ",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${spaceGrotesk.variable} ${outfit.variable} antialiased`}
      >
        <Providers>
          <div className="grid grid-rows-[auto_1fr] h-svh">
            {/* <Header /> */}
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
