import type { Metadata } from "next";
import "./tokens.css";
import { SiteNav, SiteFooter } from "./components/site-chrome";

export const metadata: Metadata = {
  title: "Autonomous Agent — Software delivery that proves itself",
  description:
    "Independent, evidence-backed verification for autonomous software delivery — not the agent's word for it.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          background: "var(--canvas)",
          color: "var(--text)",
          fontFamily: "var(--font-sans)",
          fontWeight: 400,
        }}
      >
        <a href="#main" style={{ position: "absolute", left: -9999, top: 0 }}>
          Skip to content
        </a>
        <SiteNav />
        <main id="main">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
