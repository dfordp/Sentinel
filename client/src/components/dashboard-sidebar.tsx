"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

const items = [
  { href: "/dashboard", label: "Home Dashboard", icon: "🏠" },
  { href: "/dashboard/issues", label: "Issues", icon: "🧾" },
  { href: "/dashboard/pull-requests", label: "Pull Requests", icon: "🔁" },
  { href: "/dashboard/repositories", label: "Repositories", icon: "📂" },
  { href: "/dashboard/organizations", label: "Organizations", icon: "🏢" },
  { href: "/dashboard/contributors", label: "Contributors", icon: "👥" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <div className="flex h-full flex-col">
      <div className="px-4 py-4">
        <div className="text-lg font-semibold">PR Sentinel</div>
      </div>
      <nav className="flex-1 px-2">
        <ul className="space-y-1">
          {items.map((it) => {
            const active = pathname === it.href
            return (
              <li key={it.href}>
                <Link
                  href={it.href}
                  className={cn(
                    "block rounded-md px-3 py-2 text-sm text-foreground hover:bg-muted",
                    active &&
                      "bg-(--color-accent) text-(--color-sidebar-primary-foreground) hover:bg-(--color-accent) outline -outline-offset-2 outline-(--color-sidebar-primary)",
                  )}
                >
                  <span aria-hidden className="mr-2">
                    {it.icon}
                  </span>
                  {it.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
      <div className="border-t px-4 py-3 text-xs text-muted-foreground">build: mvp</div>
    </div>
  )
}
