import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { IssueCategoryPie, ContributorReputationBar } from "@/components/charts"
import { getContributors, getIssuesContributorsAndClosures, getPullRequests } from "@/lib/demoData"

import { getIssueCategories } from "@/lib/demoData"

export default function DashboardHomePage() {
  const contributors = getContributors();
  const top5Contributors = contributors.slice(0, 5).map(c => ({
    name: c.author,
    score: c.weightedScore
  }));

  // Get statistics from demo data
  const { issues } = getIssuesContributorsAndClosures();
  const pullRequests = getPullRequests();
  const issueCategories = getIssueCategories();
  
  const totalIssues = issues.length;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const openIssues = issues.filter((issue: any) => issue.state === "open").length;
  const totalPRs = pullRequests.length;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const openPRs = pullRequests.filter((pr: any) => pr.state === "open").length;
  
  // Get most active contributors (top 3 from this week)
  const activeContributors = contributors.slice(0, 3);
  
  // Get similar PRs (PRs with related field populated)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const similarPRs = pullRequests.filter((pr: any) => pr.related && pr.related.length > 0);
  
  // Get recent high relevance items for AI highlights
  const recentHighlights = [...issues, ...pullRequests]
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .filter((item: any) => item.relevance_score && item.relevance_score >= 70)
    .slice(0, 5);

  return (
    <div className="grid gap-6">
      <section className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-3 bg-card border border-border">
          <CardHeader>
            <CardTitle className="text-card-foreground">Repo Overview</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {totalIssues + totalPRs} total items • Issues: {openIssues} open ({totalIssues} total) • PRs: {openPRs} open ({totalPRs} total)
          </CardContent>
        </Card>

        <Card className="bg-card border border-border">
          <CardHeader>
            <CardTitle className="text-card-foreground">Top Similar PRs Detected</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <p className="mb-2">Similar PRs are surfaced automatically using embeddings.</p>
            <p className="font-semibold text-card-foreground">{similarPRs.length} similar PR groups detected</p>
          </CardContent>
        </Card>
        <Card className="bg-card border border-border">
          <CardHeader>
            <CardTitle className="text-card-foreground">Most Active Contributors</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <p className="mb-2">Top contributors by weighted score:</p>
            <div className="space-y-1">
              {activeContributors.map((c, i) => (
                <div key={i} className="flex justify-between">
                  <span className="text-card-foreground">{c.author}</span>
                  <span className="font-mono">Score: {c.weightedScore}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card border border-border">
          <CardHeader>
            <CardTitle className="text-card-foreground">Recent AI Highlights</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <p className="mb-2">High relevance items (score ≥ 70):</p>
            <p className="font-semibold text-card-foreground">{recentHighlights.length} noteworthy items</p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <Card className="bg-card border border-border">
          <CardHeader>
            <CardTitle className="text-card-foreground">Issue Categories</CardTitle>
          </CardHeader>
          <CardContent>
            <IssueCategoryPie data={issueCategories} />
          </CardContent>
        </Card>
        <Card className="bg-card border border-border">
          <CardHeader>
            <CardTitle className="text-card-foreground">Top 5 Contributors</CardTitle>
          </CardHeader>
          <CardContent>
            <ContributorReputationBar data={top5Contributors} />
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
