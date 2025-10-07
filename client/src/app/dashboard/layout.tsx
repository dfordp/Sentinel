import type React from "react"
import { Sidebar } from "@/components/dashboard-sidebar"
import { DashboardHeader } from "@/components/dashboard-header"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="grid min-h-screen grid-cols-1 bg-background md:grid-cols-[260px_1fr]">
      <aside className="border-r border-sidebar-border bg-sidebar">
        <Sidebar />
      </aside>
      <div className="flex min-w-0 flex-col bg-background">
        <DashboardHeader />
        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  )
}
