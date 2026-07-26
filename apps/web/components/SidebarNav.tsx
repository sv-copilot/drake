'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FolderKanban,
  Layers,
  Play,
  Terminal,
  Wrench,
  GitPullRequest,
  Rocket,
} from 'lucide-react';

const readNavItems = [
  { href: '/operations', label: 'Operations', icon: LayoutDashboard },
  { href: '/projects', label: 'Projects', icon: FolderKanban },
  { href: '/slices', label: 'Slices', icon: Layers },
  { href: '/runs', label: 'Runs', icon: Play },
  { href: '/mcp', label: 'MCP', icon: Terminal },
  { href: '/workers', label: 'Workers', icon: Wrench },
];

const writeNavItems = [
  { href: '/ci-pr', label: 'CI/PR', icon: GitPullRequest },
  { href: '/dispatches', label: 'Dispatches', icon: Rocket },
];

export function SidebarNav() {
  const pathname = usePathname();

  const linkClasses = (href: string) =>
    cn(
      'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
      pathname === href
        ? 'bg-accent text-accent-foreground'
        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
    );

  return (
    <nav className="flex flex-col gap-1 p-4">
      <div className="mb-4">
        <h2 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Operations
        </h2>
        {readNavItems.map((item) => (
          <Link key={item.href} href={item.href} className={linkClasses(item.href)}>
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        ))}
      </div>
      <div className="border-t pt-4">
        <h2 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Control
        </h2>
        {writeNavItems.map((item) => (
          <Link key={item.href} href={item.href} className={linkClasses(item.href)}>
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}