"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"

export function LandingHero() {
  return (
    <section className="relative overflow-hidden bg-background pt-24" aria-labelledby="hero-title">
      <div
        className="absolute inset-0 -z-10 opacity-50"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(1200px 600px at 20% -10%, var(--color-primary) 0%, transparent 60%), radial-gradient(1000px 500px at 80% 10%, var(--color-accent) 0%, transparent 50%)",
        }}
      />
      <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
        <header className="mb-10 text-center">
          <h1 id="hero-title" className="text-balance text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
            {"Understand your open source contributions at a glance."}
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-pretty text-lg text-muted-foreground">
            {"PR Sentinel helps maintainers surface valuable PRs and community insights — powered by AI and GitHub."}
          </p>
        </header>

        <div className="flex items-center justify-center gap-3">
          <Button asChild size="lg" className="bg-primary text-primary-foreground hover:bg-primary/90">
            <Link href="/dashboard">View Demo</Link>
          </Button>
        </div>

        <div className="mt-14 flex justify-center">
          <div className="w-full max-w-5xl rounded-xl border border-border bg-card/50 p-2 shadow-xl backdrop-blur-sm">
            <div className="aspect-[16/9] w-full rounded-lg bg-accent" aria-label="Dashboard preview placeholder">
              {/* In a future iteration, replace with an actual video/embed */}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
