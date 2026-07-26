import Link from "next/link";
import { 
  Activity, 
  Briefcase, 
  Layers, 
  Play, 
  Terminal, 
  HardDrive, 
  GitPullRequest, 
  Zap 
} from "lucide-react";

const primaryLinks = [
  { href: "/", label: "Operations", icon: Activity },
  { href: "/projects", label: "Projects", icon: Briefcase },
  { href: "/slices", label: "Slices", icon: Layers },
  { href: "/runs", label: "Runs", icon: Play },
  { href: "/mcp", label: "MCP", icon: Terminal },
  { href: "/workers", label: "Workers", icon: HardDrive },
  { href: "/ci-pr", label: "CI/PR", icon: GitPullRequest },
];

const writeLinks = [
  { href: "/dispatches", label: "Dispatches", icon: Zap },
];

export function Nav() {
  return (
    <nav className="space-y-6">
      <div>
        <h2 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Read‑only
        </h2>
        <ul className="space-y-1">
          {primaryLinks.map(({ href, label, icon: Icon }) => (
            <li key={href}>
              <Link
                href={href}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h2 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Write control
        </h2>
        <ul className="space-y-1">
          {writeLinks.map(({ href, label, icon: Icon }) => (
            <li key={href}>
              <Link
                href={href}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10"
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
