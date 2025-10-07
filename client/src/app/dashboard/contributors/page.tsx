import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ContributorReputationBar } from "@/components/charts";
import { getContributors } from "@/lib/demoData";

// Helper to get GitHub avatar URL (assuming author is GitHub username)
function getAvatarUrl(username: string) {
  return `https://github.com/${username}.png`;
}

export default function ContributorsPage() {
  const contributors = getContributors();
  const topContributors = contributors.slice(0, 5);
  const worstContributors = contributors.slice(-5);

  return (
    <div className="grid gap-8">
      <Card>
        <CardHeader>
          <CardTitle>Reputation Scoring</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Score = 
          (completed PRs × 5 + log₂(closed PRs + 1) × 2 + log₂(issues + 1) × 1)
          × average relevance
          × log₂(total contributions + 1)
          − log₂(bad items + 1) × 10
          − penalty for &quot;other&quot; and &quot;spam&quot; closure reasons
        </CardContent>
      </Card>

      <table className="min-w-full text-sm table-fixed">
      <thead>
        <tr>
          <th className="text-left px-4 py-2 w-20">Avatar</th>
          <th className="text-left px-4 py-2">Name</th>
          <th className="text-left px-4 py-2">Score</th>
          <th className="text-left px-4 py-2">Contributions</th>
        </tr>
      </thead>
      <tbody>
        {contributors.map(c => (
          <tr key={c.author} className="h-14 align-middle">
            <td className="px-4 py-2">
              <img
                src={getAvatarUrl(c.author)}
                alt={c.author}
                className="w-8 h-8 rounded-full"
              />
            </td>
            <td className="px-4 py-2">{c.author}</td>
            <td className="px-4 py-2">{c.weightedScore}</td>
            <td className="px-4 py-2">{c.count}</td>
          </tr>
        ))}
      </tbody>
    </table>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Top 5 Contributors</CardTitle>
          </CardHeader>
          <CardContent>
            <ContributorReputationBar data={topContributors.map(c => ({ name: c.author, score: c.weightedScore }))} />
            <ul className="mt-6 space-y-4">
              {topContributors.map(c => (
                <li key={c.author} className="flex items-center space-x-3">
                  <img
                    src={getAvatarUrl(c.author)}
                    alt={c.author}
                    className="w-8 h-8 rounded-full"
                  />
                  <span className="font-medium">{c.author}</span>
                  <span className="text-xs text-muted-foreground">({c.count} contributions)</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Worst 5 Contributors</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="mt-2 space-y-4">
              {worstContributors.map(c => (
                <li key={c.author} className="flex items-center space-x-3">
                  <img
                    src={getAvatarUrl(c.author)}
                    alt={c.author}
                    className="w-8 h-8 rounded-full"
                  />
                  <span className="font-medium">{c.author}</span>
                  <span className="text-xs text-muted-foreground">({c.weightedScore} score)</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New Contributors</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {contributors.length === 0 ? "None yet." : (
            <ul className="flex flex-wrap gap-4 mt-2">
              {contributors
                .filter(c => c.count === 1)
                .map(c => (
                  <li key={c.author} className="flex items-center space-x-2">
                    <img
                      src={getAvatarUrl(c.author)}
                      alt={c.author}
                      className="w-6 h-6 rounded-full"
                    />
                    <span>{c.author}</span>
                  </li>
                ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}