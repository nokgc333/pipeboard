import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PipeBoard mini",
  description: "ショット/アセット進捗管理ミニダッシュボード",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <header className="border-b border-slate-200 bg-white px-6 py-4">
          <h1 className="text-lg font-bold text-slate-800">PipeBoard mini</h1>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
