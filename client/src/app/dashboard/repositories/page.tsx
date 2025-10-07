import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function RepositoriesPage() {
  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Repositories</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Button>Load New Repo</Button>
            <Button variant="outline">Unload Repo</Button>
          </div>
          <div className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
            Embedding in progress… <span className="animate-pulse">●</span>
          </div>
          <div className="text-xs text-muted-foreground">Last sync: —</div>
        </CardContent>
      </Card>
    </div>
  )
}
