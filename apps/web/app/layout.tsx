import type { Metadata } from "next";

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
          background: "#0A0B0D",
          color: "#F5F7FA",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif",
        }}
      >
        {children}
      </body>
    </html>
  );
}
