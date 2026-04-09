import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NUS Course Selection Agent",
  description: "Advanced preference-aware course recommendation for NUS students.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
