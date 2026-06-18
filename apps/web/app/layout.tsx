import type { Metadata } from "next";

import "./styles.css";

export const metadata: Metadata = {
  title: "Zulu Command Center",
  description:
    "Stocks and options trading intelligence with risk-governed automation controls.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
