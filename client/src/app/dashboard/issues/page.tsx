import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getIssuesContributorsAndClosures } from "@/lib/demoData";

// Helper to get GitHub avatar URL (assuming author is GitHub username)
function getAvatarUrl(username: string) {
  return `https://github.com/${username}.png`;
}

// Tabs for segregation - spam, stale and open issues
const TABS = [
  { key: "spam", label: "Spam" },
  { key: "n/a", label: "Open" },
];

function getTabIssues(issues, tab) {
  if (tab === "spam") return issues.filter(i => i.closure_reason === "spam");
  if (tab === "stale") return issues.filter(i => i.closure_reason === "stale");
  if (tab === "n/a") return issues.filter(i => i.closure_reason === "n/a");
  // Default shows all other closed issues
  return issues.filter(i => 
    i.closure_reason !== "spam" && 
    i.closure_reason !== "stale" && 
    i.closure_reason !== "n/a"
  );
}

export default function IssuesPage({ selectedContributor = "", selectedClosure = "", activeTab = "other", visibleCount = 6 }) {
  const { issues, contributors, closureReasons } = getIssuesContributorsAndClosures();

  // Filter by selection criteria
  const filteredBySelections = issues.filter(issue => {
    const contributorMatch = selectedContributor ? issue.author === selectedContributor : true;
    const closureMatch = selectedClosure ? issue.closure_reason === selectedClosure : true;
    return contributorMatch && closureMatch;
  });

  // Get tab-specific issues
  const filteredIssues = getTabIssues(filteredBySelections, activeTab);

  // Tab counts
  const tabCounts = TABS.map(tab => ({
    ...tab,
    count: getTabIssues(issues, tab.key).length
  }));

  // Count for other issues (closed but not spam or stale)
  const otherCount = issues.filter(i => 
    i.closure_reason !== "spam" && 
    i.closure_reason !== "stale" && 
    i.closure_reason !== "n/a"
  ).length;

  return (
    <div className="grid gap-6">
      <Card className="bg-card shadow-md border border-border">
        <CardHeader className="">
          <CardTitle className="text-card-foreground text-lg">Issue Filters</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="flex gap-4 flex-wrap">
            <div>
              <label className="block text-xs mb-1 font-medium text-foreground">Contributor</label>
              <select className="border border-border rounded-md px-3 py-2 bg-secondary text-foreground" defaultValue={selectedContributor} disabled>
                <option value="">All</option>
                {contributors.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs mb-1 font-medium text-foreground">Closure Reason</label>
              <select className="border border-border rounded-md px-3 py-2 bg-secondary text-foreground" defaultValue={selectedClosure} disabled>
                <option value="">All</option>
                {closureReasons.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-4 mb-4">
        {/* Tabs for spam, stale, and open issues */}
        {tabCounts.map(tab => (
          <button
            key={tab.key}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === tab.key 
                ? "bg-primary text-primary-foreground shadow-md" 
                : "bg-card text-card-foreground hover:bg-accent border border-border"
            }`}
            disabled={activeTab === tab.key}
          >
            {tab.label} <span className={`inline-block text-xs px-2 py-0.5 rounded-full ml-1 ${
              activeTab === tab.key ? "bg-primary-foreground/20" : "bg-muted"
            }`}>{tab.count}</span>
          </button>
        ))}
        
        {/* Other tab for all closed issues that aren't spam or stale */}
        <button
          className={`px-4 py-2 rounded-md font-medium transition-colors ${
            activeTab !== "spam" && activeTab !== "stale" && activeTab !== "n/a"
              ? "bg-primary text-primary-foreground shadow-md" 
              : "bg-card text-card-foreground hover:bg-accent border border-border"
          }`}
          disabled={activeTab !== "spam" && activeTab !== "stale" && activeTab !== "n/a"}
        >
          Other <span className={`inline-block text-xs px-2 py-0.5 rounded-full ml-1 ${
            activeTab !== "spam" && activeTab !== "stale" && activeTab !== "n/a" ? "bg-primary-foreground/20" : "bg-muted"
          }`}>{otherCount}</span>
        </button>
      </div>

      <div className="w-full flex flex-col gap-6">
        {filteredIssues.slice(0, visibleCount).map(issue => (
          <Card key={issue.id} className="border border-border shadow-lg overflow-hidden bg-card">
            <CardHeader className="bg-gradient-to-r from-secondary to-card border-b border-border pb-3">
              <div className="flex items-center gap-4">
                <img
                  src={getAvatarUrl(issue.author)}
                  alt={issue.author}
                  className="w-10 h-10 rounded-full border-2 border-border shadow"
                />
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-lg font-semibold text-card-foreground">
                      {issue.type === "issue" ? "Issue" : "PR"} #{issue.number}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground font-medium">
                        Relevance: {issue.relevance_score}
                      </span>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground font-medium mt-1">{issue.author}</div>
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {/* Show closure reason as badge */}
                    <span className={`px-2 py-1 rounded-full text-xs font-bold shadow-sm
                      ${issue.closure_reason === "spam" ? "bg-red-500 text-white"
                        : issue.closure_reason === "stale" ? "bg-yellow-400 text-black"
                        : issue.closure_reason === "completed" ? "bg-green-500 text-white"
                        : issue.closure_reason === "wontfix" ? "bg-purple-500 text-white"
                        : issue.closure_reason === "invalid" ? "bg-orange-500 text-white"
                        : issue.closure_reason === "n/a" ? "bg-blue-400 text-white"
                        : "bg-gray-300 text-black"}`}>
                      {issue.closure_reason}
                    </span>
                    <span className={`px-2 py-1 rounded-full text-xs font-bold shadow-sm
                      ${issue.state === "open" ? "bg-blue-500 text-white" : "bg-gray-500 text-white"}`}>
                      {issue.state}
                    </span>
                    {/* Additional tags as badges */}
                    {issue.labels && issue.labels.map(label => (
                      <span key={label} className="px-2 py-1 rounded-full bg-primary/20 text-primary text-xs shadow-sm">{label}</span>
                    ))}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="mb-4">
                <span className="font-semibold text-foreground">Summary:</span>
                <div className="text-sm mt-1 bg-secondary text-secondary-foreground p-3 rounded-md">{issue.summary}</div>
              </div>
              
              <div className="mb-4">
                <span className="font-semibold text-foreground">Difference Analysis:</span>
                <div className="text-xs mt-1 bg-secondary text-secondary-foreground p-3 rounded-md">{issue.difference_analysis}</div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <span className="font-semibold text-foreground">Best in Group:</span> 
                  <span className={`ml-2 ${issue.best_in_group === "true" ? "text-green-400" : "text-red-400"}`}>
                    {issue.best_in_group}
                  </span>
                </div>
                
                <div>
                  <span className="font-semibold text-foreground">Matches Requirements:</span> 
                  <span className={`ml-2 ${issue.matches_requirements ? "text-green-400" : "text-red-400"}`}>
                    {issue.matches_requirements ? "Yes" : "No"}
                  </span>
                </div>
              </div>
              
              <div className="mt-4">
                <span className="font-semibold text-foreground">Best Rationale:</span>
                <div className="text-xs mt-1 bg-secondary text-secondary-foreground p-3 rounded-md">{issue.best_rationale}</div>
              </div>
              
              {issue.related && issue.related.length > 0 && (
                <div className="mt-4">
                  <span className="font-semibold text-foreground">Related Issues:</span>
                  <div className="flex gap-2 mt-1">
                    {issue.related.map(rel => (
                      <span key={rel} className="px-2 py-1 bg-primary/20 text-primary rounded-md text-xs">{rel}</span>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {filteredIssues.length > visibleCount && (
          <button
            className="mt-4 px-6 py-3 rounded-md bg-primary text-primary-foreground font-medium self-center hover:bg-primary/90 transition-colors shadow-md"
            disabled
          >
            See More Issues
          </button>
        )}
      </div>
    </div>
  );
}