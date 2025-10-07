import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function PullRequestsPage() {
  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Pull Requests</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Table placeholder: PR title • Contributor • Similar • AI Summary • Status
        </CardContent>
      </Card>
    </div>
  )
}
