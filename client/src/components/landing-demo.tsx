"use client"

import { Button } from "@/components/ui/button"
import Link from "next/link"

export function LandingDemo() {
  return (
    <section id="demo" className="bg-background mx-auto max-w-6xl px-6 py-16 md:py-20" aria-labelledby="demo-title">
      <div className="flex items-center justify-between gap-4">
        <h2 id="demo-title" className="text-2xl font-semibold text-foreground">
          {"Demo Preview"}
        </h2>
        <Button asChild variant="outline">
          <Link href="/dashboard">View Example Dashboard</Link>
        </Button>
      </div>

      <div className="mt-6 overflow-hidden rounded-xl border border-border bg-card shadow-xl backdrop-blur-sm">
        <div className="aspect-[16/9] w-full bg-accent" aria-label="Demo video placeholder" />
      </div>
    </section>
  )
}
