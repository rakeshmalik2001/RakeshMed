import type { Metadata } from "next";
import { Manrope, Public_Sans } from "next/font/google";
import type { ReactNode } from "react";

import { CartProvider } from "@/components/cart-provider";
import { CustomerActivityTracker } from "@/components/customer-activity-tracker";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrueCare Pharmacy",
  description: "A modern pharmacy storefront focused on trusted guidance, medicine savings, and faster care access."
};

const publicSans = Public_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap"
});

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap"
});

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${publicSans.variable} ${manrope.variable}`}>
      <body className={publicSans.className}>
        <CartProvider>
          <CustomerActivityTracker />
          <div className="app-shell">{children}</div>
        </CartProvider>
      </body>
    </html>
  );
}
