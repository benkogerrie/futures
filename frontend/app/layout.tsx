import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Quant Trading Dashboard",
  description: "Dark-mode quant dashboard for NDQ exposure management.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
