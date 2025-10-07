export function LandingHowItWorks() {
  const steps = [
    { title: "Load your repository", desc: "Connect via GitHub App." },
    { title: "We embed and analyze", desc: "PRs and issues become searchable vectors." },
    { title: "Get your insights", desc: "Interactive dashboard highlights what matters." },
  ]

  return (
    <section id="how-it-works" className="bg-background mx-auto max-w-6xl px-6 py-16 md:py-20" aria-labelledby="how-title">
      <h2 id="how-title" className="text-2xl font-semibold text-foreground">
        {"How It Works"}
      </h2>
      <ol className="mt-6 grid gap-4 md:grid-cols-3">
        {steps.map((s, i) => (
          <li key={i} className="rounded-xl border border-border bg-card p-5 backdrop-blur-sm">
            <div className="text-sm font-mono text-muted-foreground">Step {i + 1}</div>
            <div className="mt-2 text-lg font-medium text-card-foreground">{s.title}</div>
            <p className="mt-1 text-muted-foreground">{s.desc}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
