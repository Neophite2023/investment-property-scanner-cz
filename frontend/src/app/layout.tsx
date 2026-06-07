import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { ServiceWorkerRegister } from "./sw-register";

export const metadata: Metadata = {
  title: "Investment Property Scanner CZ",
  description: "Dashboard pre vyhľadávanie investičných bytov v ČR",
  manifest: "/manifest.webmanifest"
};

export const viewport: Viewport = {
  themeColor: "#52745f",
  width: "device-width",
  initialScale: 1
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="sk">
      <body>
        <ServiceWorkerRegister />
        {children}
      </body>
    </html>
  );
}
