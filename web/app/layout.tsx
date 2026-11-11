import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lollipop: bipartite search for graph researchers",
  description:
    "Lollipop writes short programs that leave a dense piece of a bipartite graph, then scores how much of a planted piece comes back.",
  openGraph: {
    type: "website",
    title: "Lollipop: bipartite search for graph researchers",
    description:
      "Short programs discard vertices until a bipartite graph leaves a γ-quasi-biclique. Recovery of a planted piece is the score.",
    images: ["/share.jpg"],
  },
  twitter: { card: "summary_large_image" },
  icons: { icon: "/lollipop.png" },
};

export const viewport: Viewport = {
  themeColor: "#f6f3f4",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      data-type="software"
      data-radius="sharp"
      data-buttons="pill"
      data-motion=""
    >
      <head>
        <meta name="site-kind" content="software" />
        <meta name="page-type" content="software" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Funnel+Display:wght@400..700&family=Funnel+Sans:wght@400..600&family=DM+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <link rel="stylesheet" href="/assets/system.css" />
        <link rel="stylesheet" href="/assets/ui/cards.css" />
        <link rel="stylesheet" href="/assets/motion/motion.css" />
        <link rel="stylesheet" href="/assets/backgrounds/backgrounds.css" />
        <link rel="stylesheet" href="/assets/layout/layout.css" />
        <link rel="stylesheet" href="/assets/icons/icon.css" />
        <link rel="stylesheet" href="/assets/ui/base.css" />
        <link rel="stylesheet" href="/assets/ui/window/fragment.css" />
        <link rel="stylesheet" href="/assets/ui/code/fragment.css" />
        <link rel="stylesheet" href="/assets/ui/checklist/fragment.css" />
        <link rel="stylesheet" href="/assets/ui/notify/fragment.css" />
        <link rel="stylesheet" href="/page.css" />
        <style>{`:root {
  --p-bg: #f6f3f4; --p-surface: #ebe4e7; --p-ink: #1a1216; --p-muted: #655e61;
  --p-accent: #c2186a; --p-accent-ink: #f6f3f4; --p-action: #c2186a; --p-action-ink: #f6f3f4;
  --p-inv-bg: #1a1216; --p-inv-surface: #271e22; --p-inv-ink: #f6f3f4; --p-inv-muted: #9a9497;
  --p-inv-accent: #c2186a; --p-inv-accent-ink: #f6f3f4; --p-inv-action: #c2186a; --p-inv-action-ink: #f6f3f4;
  --font-display: "Funnel Display", system-ui, sans-serif;
  --font-text: "Funnel Sans", system-ui, sans-serif;
  --font-mono: "DM Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  --display-weight: 400;
  --display-tracking: -0.03em;
  --display-tracking-xl: -0.04em;
  --ly-scale: 0.98;
}`}</style>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "document.documentElement.classList.add('m-enter');setTimeout(()=>document.documentElement.classList.add('m-enter-done'),700)",
          }}
        />
        <script
          dangerouslySetInnerHTML={{
            __html:
              "document.documentElement.classList.add('mo-js');setTimeout(()=>document.documentElement.classList.add('mo-safe'),2500)",
          }}
        />
        <link rel="modulepreload" href="/assets/moments/moments.js" />
        <link rel="modulepreload" href="/assets/moments/lib.js" />
        <link rel="modulepreload" href="/assets/moments/liquid-type/moment.js" />
        <script src="/assets/backgrounds/backgrounds.js" />
      </head>
      <body>
        {children}
        <script type="module" src="/assets/system.js" />
        <script type="module" src="/assets/motion/motion.js" />
        <script type="module" src="/assets/layout/layout.js" />
      </body>
    </html>
  );
}
