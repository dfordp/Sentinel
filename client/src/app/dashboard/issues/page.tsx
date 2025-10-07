import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function IssuesPage() {
  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Issues</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Table placeholder: Issue title • Similar PRs • Duplicate detection
        </CardContent>
      </Card>
    </div>
  )
}
