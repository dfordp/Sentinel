import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function LandingProblemSolution() {
  return (
    <section id="features" className="bg-background mx-auto max-w-6xl px-6 py-16 md:py-20" aria-labelledby="problems-title">
      <h2 id="problems-title" className="text-2xl font-semibold text-foreground">
        {"Problem & Solution"}
      </h2>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Card className="border-border bg-card backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-card-foreground">Noise</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground">
            {"Spam, duplicates, and low-effort PRs clutter triage."}
          </CardContent>
        </Card>
        <Card className="border-border bg-card backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-card-foreground">Context</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground">
            {"Relating new PRs to historical issues is hard."}
          </CardContent>
        </Card>
        <Card className="border-border bg-card backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-card-foreground">Time</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground">
            {"Triage takes hours that could be spent building."}
          </CardContent>
        </Card>
      </div>

      <div className="mt-10 rounded-xl border border-border bg-card p-6 backdrop-blur-sm">
        <h3 className="text-lg font-medium text-card-foreground">Solution</h3>
        <ul className="mt-3 grid list-disc gap-1 pl-6 text-muted-foreground md:grid-cols-3">
          <li>AI-powered repo insights</li>
          <li>Similar PR/issue matching</li>
          <li>Contributor trust ranking</li>
        </ul>
      </div>
    </section>
  )
}
