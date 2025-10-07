import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export default function SettingsPage() {
  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Cleanup</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">Remove synced data for this repo.</p>
          <Button variant="destructive">Clear Data</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Background Jobs</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">No recent logs.</CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API Tokens</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">Read-only tokens will appear here.</CardContent>
      </Card>
    </div>
  )
}
