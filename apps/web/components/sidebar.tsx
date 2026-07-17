import Link from "next/link";
import {
  LayoutDashboard,
  FolderOpen,
  Layers,
  PlayCircle,
  Terminal,
  Wrench,
  GitBranch,
  Send,
} from "lucide-react";

const navItems = [
  { href: "/operations", label: "Operations", icon: LayoutDashboard, readOnly: true },
  { href: "/projects", label: "Projects", icon: FolderOpen, readOnly: true },
  { href: "/slices", label: "Slices", icon: Layers, readOnly: true },
  { href: "/runs", label: "Runs", icon: PlayCircle, readOnly: true },
  { href: "/mcp", label: "MCP", icon: Terminal, readOnly: true },
  { href: "/workers", label: "Workers", icon: Wrench, readOnly: true },
  { href: "/ci-pr", label: "CI / PR", icon: GitBranch, readOnly: true },
  { href: "/dispatches", label: "Dispatches", icon: Send, readOnly: false, write: true },
];

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-gray-50 dark:bg-gray-950">
      <div className="flex h-full flex-col gap-2 p-4">
        <div className="mb-6 flex items-center gap-2 px-2 py-3">
          <LayoutDashboard className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold">Drake Cockpit</span>
        </div>
        <nav className="flex-1 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground ${
                item.write
                  ? "border border-destructive/30 text-destructive hover:bg-destructive/10"
                  : "text-muted-foreground"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
              {item.write && (
                <span className="ml-auto text-xs font-normal uppercase tracking-wider text-destructive">
                  write
                </span>
              )}
            </Link>
          ))}
        </nav>
        <div className="border-t pt-4 text-xs text-muted-foreground">
          <p>Read‑only by default</p>
          <p>Full auth boundary provided by #75</p>
        </div>
      </div>
    </aside>
  );
}
