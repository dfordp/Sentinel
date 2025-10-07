import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { IssueCategoryPie, ContributorReputationBar } from "@/components/charts"

export default function DashboardHomePage() {
  return (
    <div className="grid gap-6">
      <section className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-3">
          <CardHeader>
            <CardTitle>Repo Overview</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Example Repo • ⭐ 3,142 • Issues: 42 open • PRs: 17 open
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Similar PRs Detected</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Similar PRs are surfaced automatically using embeddings.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Most Active Contributors</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            See who’s actively contributing this week.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recent AI Highlights</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Concise summaries of noteworthy activity in your repo.
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Issue Categories</CardTitle>
          </CardHeader>
          <CardContent>
            <IssueCategoryPie />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Contributor Reputation</CardTitle>
          </CardHeader>
          <CardContent>
            <ContributorReputationBar />
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
