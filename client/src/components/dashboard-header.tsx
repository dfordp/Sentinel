"use client"

import { Button } from "@/components/ui/button"
import { RefreshCw } from "lucide-react"

export function DashboardHeader() {
  return (
    <header className="flex items-center justify-between gap-3 border-b border-border bg-card px-4 py-3">
      <div className="min-w-0">
        <h1 className="truncate text-lg font-semibold text-card-foreground">Example Repo</h1>
        <p className="truncate text-sm text-muted-foreground">Last synced: just now • Status: idle</p>
      </div>
      <div className="flex items-center gap-2">
        <Button size="icon" variant="outline" aria-label="Refresh">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
