import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ContributorReputationBar } from "@/components/charts"

export default function ContributorsPage() {
  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Reputation Scoring</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">Score = f(# PRs, merge ratio, recency)</CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Top 5 Contributors</CardTitle>
        </CardHeader>
        <CardContent>
          <ContributorReputationBar />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>New Contributors</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">None yet.</CardContent>
      </Card>
    </div>
  )
}
