export function LandingRoadmap() {
  const items = ["Multi-repo view", "Contributor trust graph", "Spam detection engine"]
  return (
    <section className="bg-background mx-auto max-w-6xl px-6 py-16 md:py-20" aria-labelledby="roadmap-title">
      <h2 id="roadmap-title" className="text-2xl font-semibold text-foreground">
        {"Coming Soon"}
      </h2>
      <ul className="mt-4 grid gap-3 md:grid-cols-3">
        {items.map((t) => (
          <li key={t} className="rounded-xl border border-border bg-card px-5 py-4 text-muted-foreground backdrop-blur-sm">
            {t}
          </li>
        ))}
      </ul>
    </section>
  )
}
