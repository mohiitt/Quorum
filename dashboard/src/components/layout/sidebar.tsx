"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Zap, Shield } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/demo", label: "Live Demo", icon: Zap, highlight: true },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-zinc-800 bg-zinc-900">
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-zinc-800 px-6 gap-2">
        <Shield className="h-5 w-5 text-emerald-400 shrink-0" />
        <span className="font-mono text-lg font-bold tracking-widest text-zinc-50">
          QUORUM
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map(({ href, label, icon: Icon, highlight }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? highlight
                    ? "bg-emerald-900/50 text-emerald-300 border border-emerald-800/60"
                    : "bg-zinc-800 text-zinc-50"
                  : highlight
                    ? "text-emerald-400 hover:bg-emerald-900/30 hover:text-emerald-300"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-50"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
              {highlight && !active && (
                <span className="ml-auto text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-700 rounded px-1">
                  NEW
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Connection status */}
      <div className="border-t border-zinc-800 px-5 py-4 space-y-1">
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          Quorum Active
        </div>
        <p className="text-[10px] text-zinc-600">Trust & Consensus Layer</p>
      </div>
    </aside>
  );
}
