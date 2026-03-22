import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "@/components/auth/AuthProvider";

export const metadata: Metadata = {
  title: "SigmaCloud AI — AutoML Platform",
  description: "Upload datasets, train models automatically, visualize results, and deploy predictions.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
        <AuthProvider>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                background: "#202a33",
                color: "#f8f4ef",
                border: "1px solid rgba(170,205,220,0.32)",
                fontFamily: "'DM Sans', sans-serif",
              },
            }}
          />
        </AuthProvider>
      </body>
    </html>
  );
}
