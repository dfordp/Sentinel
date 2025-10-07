import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getIssuesAndPRsContributorsAndClosures } from "@/lib/demoData";

// Helper to get GitHub avatar URL (assuming author is GitHub username)
function getAvatarUrl(username: string) {
  return `https://github.com/${username}.png`;
}

// Tabs for segregation - spam, stale and open issues
const TABS = [
  { key: "spam", label: "Spam" },
  { key: "n/a", label: "Open" },
  { key: "other", label: "Other" },
];

function getTabItems(items, tab) {
  if (tab === "spam") return items.filter(i => i.closure_reason === "spam");
  if (tab === "stale") return items.filter(i => i.closure_reason === "stale");
  if (tab === "n/a") return items.filter(i => i.closure_reason === "n/a");
  // Other shows all other closed items (not spam, stale or open)
  return items.filter(i => 
    i.closure_reason !== "spam" && 
    i.closure_reason !== "stale" && 
    i.closure_reason !== "n/a"
  );
}

export default function IssuesAndPRsPage({ selectedContributor = "", selectedClosure = "", activeTab = "other", visibleCount = 30 }) {
  const { allItems, contributors, closureReasons } = getIssuesAndPRsContributorsAndClosures();

  // Filter by selection criteria
  const filteredBySelections = allItems.filter(item => {
    const contributorMatch = selectedContributor ? item.author === selectedContributor : true;
    const closureMatch = selectedClosure ? item.closure_reason === selectedClosure : true;
    return contributorMatch && closureMatch;
  });

  // Get tab-specific items
  const filteredItems = getTabItems(filteredBySelections, activeTab);

  // Tab counts
  const tabCounts = TABS.map(tab => ({
    ...tab,
    count: getTabItems(allItems, tab.key).length
  }));

  return (
    <div className="grid gap-6">
      <Card className="bg-white shadow-md border-0">
        <CardHeader className="bg-slate-50 rounded-t-lg">
          <CardTitle>Content Filters</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="flex gap-4 flex-wrap">
            <div>
              <label className="block text-xs mb-1 font-medium">Contributor</label>
              <select className="border rounded-md px-3 py-2 bg-white" defaultValue={selectedContributor} disabled>
                <option value="">All</option>
                {contributors.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs mb-1 font-medium">Closure Reason</label>
              <select className="border rounded-md px-3 py-2 bg-white" defaultValue={selectedClosure} disabled>
                <option value="">All</option>
                {closureReasons.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2 mb-4">
        {/* Tabs for spam, stale, open, and other */}
        {tabCounts.map(tab => (
          <button
            key={tab.key}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === tab.key 
                ? "bg-blue-600 text-white shadow-md" 
                : "bg-white text-gray-700 hover:bg-gray-50 border"
            }`}
            disabled={activeTab === tab.key}
          >
            {tab.label} <span className="inline-block bg-white bg-opacity-20 text-xs px-2 py-0.5 rounded-full ml-1">{tab.count}</span>
          </button>
        ))}
      </div>

      <div className="w-full flex flex-col gap-6">
        {filteredItems.slice(0, visibleCount).map(item => (
          <Card key={item.id} className="border-0 shadow-lg overflow-hidden">
            <CardHeader className="bg-gradient-to-r from-slate-50 to-white border-b pb-3">
              <div className="flex items-center gap-4">
                <img
                  src={getAvatarUrl(item.author)}
                  alt={item.author}
                  className="w-10 h-10 rounded-full border-2 border-white shadow"
                />
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-lg font-semibold">
                      {item.type === "issue" ? "Issue" : "PR"} #{item.number}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500 font-medium">
                        Relevance: {item.relevance_score}
                      </span>
                    </div>
                  </div>
                  <div className="text-sm text-gray-600 font-medium mt-1">{item.author}</div>
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {/* Show closure reason as badge */}
                    <span className={`px-2 py-1 rounded-full text-xs font-bold shadow-sm
                      ${item.closure_reason === "spam" ? "bg-red-500 text-white"
                        : item.closure_reason === "stale" ? "bg-yellow-400 text-black"
                        : item.closure_reason === "completed" ? "bg-green-500 text-white"
                        : item.closure_reason === "wontfix" ? "bg-purple-500 text-white"
                        : item.closure_reason === "invalid" ? "bg-orange-500 text-white"
                        : item.closure_reason === "n/a" ? "bg-blue-400 text-white"
                        : "bg-gray-300 text-black"}`}>
                      {item.closure_reason}
                    </span>
                    <span className={`px-2 py-1 rounded-full text-xs font-bold shadow-sm
                      ${item.state === "open" ? "bg-blue-500 text-white" : "bg-gray-500 text-white"}`}>
                      {item.state}
                    </span>
                    <span className={`px-2 py-1 rounded-full text-xs font-bold shadow-sm
                      ${item.type === "issue" ? "bg-purple-100 text-purple-800" : "bg-green-100 text-green-800"}`}>
                      {item.type === "issue" ? "Issue" : "Pull Request"}
                    </span>
                    {/* Additional tags as badges */}
                    {item.labels && item.labels.map(label => (
                      <span key={label} className="px-2 py-1 rounded-full bg-blue-100 text-blue-800 text-xs shadow-sm">{label}</span>
                    ))}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="mb-4">
                <span className="font-semibold">Summary:</span>
                <div className="text-sm mt-1 bg-slate-50 p-3 rounded-md">{item.summary}</div>
              </div>
              
              <div className="mb-4">
                <span className="font-semibold">Difference Analysis:</span>
                <div className="text-xs mt-1 bg-slate-50 p-3 rounded-md">{item.difference_analysis}</div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <span className="font-semibold">Best in Group:</span> 
                  <span className={`ml-2 ${item.best_in_group === "true" ? "text-green-600" : "text-red-600"}`}>
                    {item.best_in_group}
                  </span>
                </div>
                
                <div>
                  <span className="font-semibold">Matches Requirements:</span> 
                  <span className={`ml-2 ${item.matches_requirements ? "text-green-600" : "text-red-600"}`}>
                    {item.matches_requirements ? "Yes" : "No"}
                  </span>
                </div>
              </div>
              
              <div className="mt-4">
                <span className="font-semibold">Best Rationale:</span>
                <div className="text-xs mt-1 bg-slate-50 p-3 rounded-md">{item.best_rationale}</div>
              </div>
              
              {item.related && item.related.length > 0 && (
                <div className="mt-4">
                  <span className="font-semibold">Related Issues:</span>
                  <div className="flex gap-2 mt-1">
                    {item.related.map(rel => (
                      <span key={rel} className="px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-xs">{rel}</span>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {filteredItems.length > visibleCount && (
          <button
            className="mt-4 px-6 py-3 rounded-md bg-blue-600 text-white font-medium self-center hover:bg-blue-700 transition-colors shadow-md"
            disabled
          >
            See More Content
          </button>
        )}
      </div>
    </div>
  );
}