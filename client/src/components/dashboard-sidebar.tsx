"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Home, FolderCode, BadgeAlert, Building2 } from "lucide-react"
import { FaCodePullRequest } from "react-icons/fa6"
import { IoPeopleSharp } from "react-icons/io5"
import { IoMdSettings } from "react-icons/io"

const items = [
  { href: "/dashboard", label: "Home Dashboard", icon: Home },
  { href: "/dashboard/issues", label: "Issues", icon: BadgeAlert },
  { href: "/dashboard/pull-requests", label: "Pull Requests", icon: FaCodePullRequest },
  { href: "/dashboard/contributors", label: "Contributors", icon: IoPeopleSharp },
  { href: "/dashboard/repositories", label: "Repositories", icon: FolderCode },
  { href: "/dashboard/organizations", label: "Organizations", icon: Building2 },
  { href: "/dashboard/settings", label: "Settings", icon: IoMdSettings },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <div className="flex h-full flex-col bg-sidebar">
      <div className="px-4 py-6">
        <div className="text-lg font-semibold text-sidebar-foreground">OpenLens</div>
      </div>
      <nav className="flex-1 px-3">
        <ul className="space-y-0.5">
          {items.map((it) => {
            const active = pathname === it.href
            return (
              <li key={it.href}>
                <Link
                  href={it.href}
                  className={cn(
                    "flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                    active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground hover:bg-sidebar-accent"
                      : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  )}
                >
                  <it.icon className="mr-3 h-4 w-4" aria-hidden />
                  {it.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
      <div className="border-t border-sidebar-border px-4 py-3 text-xs text-muted-foreground">build: mvp</div>
    </div>
  )
}
