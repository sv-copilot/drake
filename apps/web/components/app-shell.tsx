"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Boxes,
  GitPullRequest,
  History,
  LayoutDashboard,
  Send,
  RefreshCw,
} from "lucide-react";
import { type ReactNode } from "react";

import { getApiBaseUrl } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const navItems = [
  {
    href: "/portfolio",
    label: "Portfolio",
    description: "Registered repos and readiness",
    icon: LayoutDashboard,
  },
  {
    href: "/slices",
    label: "Slices",
    description: "Dependency states and gates",
    icon: Boxes,
  },
  {
    href: "/runs",
    label: "Runs",
    description: "Evidence and validation history",
    icon: History,
  },
  {
    href: "/sync",
    label: "Sync",
    description: "Read cache freshness and source files",
    icon: RefreshCw,
  },
  {
    href: "/workers",
    label: "Workers",
    description: "Adapter status by runtime",
    icon: Activity,
  },
  {
    href: "/dispatches",
    label: "Dispatches",
    description: "Read-only dispatch log",
    icon: Send,
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-stone-50 text-slate-950">
      <div className="mx-auto flex min-h-screen max-w-7xl">
        <aside className="hidden w-80 border-r border-stone-200 bg-white px-6 py-8 lg:block">
          <Link href="/" className="block">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              Drake
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">
              Hosted operations
            </h1>
          </Link>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Read-only control plane for repo-native governance, evidence, worker
            adapters, and MCP-backed systems.
          </p>
          <nav aria-label="Primary" className="mt-10 space-y-1">
            {navItems.map((item) => (
              <ShellNavItem
                key={item.href}
                {...item}
                active={isNavItemActive(item.href, pathname)}
              />
            ))}
          </nav>
          <div className="mt-10 rounded-lg border border-stone-200 bg-stone-50 p-4 text-sm">
            <div className="flex items-center gap-2 font-medium">
              <GitPullRequest className="h-4 w-4 text-slate-500" />
              API boundary
            </div>
            <p className="mt-2 break-all text-slate-600">
              {getApiBaseUrl()}
            </p>
            <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">
              Read-only scaffold
            </p>
          </div>
        </aside>
        <main className="flex min-w-0 flex-1 flex-col">
          <header className="border-b border-stone-200 bg-white px-5 py-4 lg:hidden">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              Drake
            </p>
            <h1 className="text-xl font-semibold">Hosted operations</h1>
          </header>
          <div className="px-5 py-8 sm:px-8 lg:px-12">{children}</div>
        </main>
      </div>
    </div>
  );
}

export function isNavItemActive(href: string, pathname: string) {
  if (pathname === href) {
    return true;
  }
  if (href === "/portfolio" && /^\/repos\/[^/]+$/.test(pathname)) {
    return true;
  }
  if (href === "/slices" && /^\/repos\/[^/]+\/slices$/.test(pathname)) {
    return true;
  }
  if (href !== "/" && pathname.startsWith(`${href}/`)) {
    return true;
  }
  return false;
}

type ShellNavItemProps = (typeof navItems)[number] & {
  active?: boolean;
  className?: string;
};

export function ShellNavItem({
  href,
  label,
  description,
  icon: Icon,
  active = false,
  className,
}: ShellNavItemProps) {
  return (
    <Link
      href={href}
      className={cn(
        "group flex gap-3 rounded-lg border-l-4 border-transparent px-3 py-3 text-left transition-colors hover:bg-stone-100",
        active && "border-slate-900 bg-stone-100 pl-3 shadow-inner",
        className,
      )}
      aria-current={active ? "page" : undefined}
    >
      <Icon
        className={cn(
          "mt-0.5 h-5 w-5 flex-none text-slate-500 transition-colors group-hover:text-slate-900",
          active && "text-slate-900",
        )}
      />
      <span>
        <span className="block text-sm font-medium text-slate-950">
          {label}
        </span>
        <span className="mt-0.5 block text-sm leading-5 text-slate-600">
          {description}
        </span>
      </span>
    </Link>
  );
}
