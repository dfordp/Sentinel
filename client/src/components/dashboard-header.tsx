"use client"

import { Button } from "@/components/ui/button"

export function DashboardHeader() {
  return (
    <header className="flex items-center justify-between gap-3 border-b bg-card px-4 py-3">
      <div className="min-w-0">
        <h1 className="truncate text-lg font-semibold">Example Repo</h1>
        <p className="truncate text-sm text-muted-foreground">Last synced: just now • Status: idle</p>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline">Settings</Button>
        <Button>Refresh</Button>
      </div>
    </header>
  )
}
