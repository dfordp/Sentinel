export function LandingHowItWorks() {
  const steps = [
    { title: "Load your repository", desc: "Connect via GitHub App." },
    { title: "We embed and analyze", desc: "PRs and issues become searchable vectors." },
    { title: "Get your insights", desc: "Interactive dashboard highlights what matters." },
  ]

  return (
    <section className="mx-auto max-w-6xl px-6 py-16 md:py-20" aria-labelledby="how-title">
      <h2 id="how-title" className="text-2xl font-semibold">
        {"How It Works"}
      </h2>
      <ol className="mt-6 grid gap-4 md:grid-cols-3">
        {steps.map((s, i) => (
          <li key={i} className="rounded-xl border bg-card p-5">
            <div className="text-sm font-mono text-muted-foreground">Step {i + 1}</div>
            <div className="mt-2 text-lg font-medium">{s.title}</div>
            <p className="mt-1 text-muted-foreground">{s.desc}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
