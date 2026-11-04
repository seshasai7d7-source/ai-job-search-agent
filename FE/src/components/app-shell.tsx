"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

const pages = [
  { label: "Overview", href: "/", icon: "⌂" },
  { label: "Jobs", href: "/jobs", icon: "◇" },
  { label: "Resume", href: "/resume", icon: "▤" },
  { label: "Applications", href: "/applications", icon: "✓" },
  { label: "Search runs", href: "/search-runs", icon: "↻" },
];

function BrandMark() {
  return (
    <div className="flex size-10 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm shadow-indigo-950/15">
      <svg
        aria-hidden="true"
        className="size-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M5 18.5V9.75a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v8.75M3.5 18.5h17M8 7.75V6.5A1.5 1.5 0 0 1 9.5 5h5A1.5 1.5 0 0 1 16 6.5v1.25M9 12h6M9 15h3"
        />
      </svg>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const pathname = usePathname();
  const linkClass = (href: string) =>
    `flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium ${
      pathname === href || (href !== "/" && pathname.startsWith(href))
        ? "bg-indigo-50 font-semibold text-indigo-700"
        : "text-slate-600 hover:bg-slate-50"
    }`;

  return (
    <div
      className="min-h-screen bg-[#f7f8fc] text-slate-950"
      data-theme={darkMode ? "dark" : "light"}
    >
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col border-r border-slate-200/80 bg-white lg:flex">
        <div className="flex h-20 items-center gap-3 px-6">
          <BrandMark />
          <div>
            <p className="text-sm font-bold tracking-tight text-slate-950">
              AI Job Search
            </p>
            <p className="mt-0.5 text-xs text-slate-500">Personal workspace</p>
          </div>
        </div>

        <nav aria-label="Main navigation" className="flex-1 px-4 py-6">
          <p className="px-3 pb-3 text-[11px] font-bold uppercase tracking-[0.15em] text-slate-400">
            Workspace
          </p>
          <div className="space-y-1">
            {pages.map((page) => (
              <Link
                aria-current={pathname === page.href || (page.href !== "/" && pathname.startsWith(page.href)) ? "page" : undefined}
                className={linkClass(page.href)}
                href={page.href}
                key={page.href}
              >
                <span aria-hidden="true" className="text-base">{page.icon}</span>
                {page.label}
              </Link>
            ))}
          </div>
        </nav>

        <div className="m-4 rounded-2xl border border-indigo-100 bg-indigo-50/70 p-4">
          <p className="text-sm font-semibold text-slate-900">Local by design</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Your job search data is managed by your local API.
          </p>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur sm:px-8 lg:h-20 lg:px-10">
          <div className="flex items-center gap-3">
            <button
              aria-expanded={menuOpen}
              aria-label={menuOpen ? "Close navigation" : "Open navigation"}
              className="inline-flex size-10 items-center justify-center rounded-lg border border-slate-200 text-slate-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 lg:hidden"
              onClick={() => setMenuOpen((open) => !open)}
              type="button"
            >
              <span aria-hidden="true" className="text-xl leading-none">
                {menuOpen ? "×" : "☰"}
              </span>
            </button>
            <div className="lg:hidden">
              <BrandMark />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">
                AI Job Search Agent
              </p>
              <p className="hidden text-xs text-slate-500 sm:block">
                Local-first career workspace
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              aria-pressed={darkMode}
              className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
              onClick={() => setDarkMode((enabled) => !enabled)}
              type="button"
            >
              {darkMode ? "Use light theme" : "Use dark theme"}
            </button>
            <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 sm:flex">
              <span className="size-2 rounded-full bg-emerald-500" />
              <span className="text-xs font-medium text-slate-600">
                Local workspace
              </span>
            </div>
          </div>
        </header>

        {menuOpen && (
          <nav
            aria-label="Mobile navigation"
            className="absolute inset-x-0 top-16 z-30 border-b border-slate-200 bg-white p-4 shadow-lg lg:hidden"
          >
            <div className="space-y-1">
              {pages.map((page) => (
                <Link
                  aria-current={pathname === page.href || (page.href !== "/" && pathname.startsWith(page.href)) ? "page" : undefined}
                  className={linkClass(page.href)}
                  href={page.href}
                  key={page.href}
                  onClick={() => setMenuOpen(false)}
                >
                  {page.label}
                </Link>
            ))}
            </div>
          </nav>
        )}

        <main className="px-4 py-8 sm:px-8 sm:py-10 lg:px-10 lg:py-12">
          {children}
        </main>
      </div>
    </div>
  );
}
