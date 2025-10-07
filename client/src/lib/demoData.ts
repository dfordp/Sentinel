import fs from "fs";
import path from "path";

// Load demo.json at runtime (works for Next.js server components)
function loadDemoData() {
  try {
    // Always resolve from project root, not drive root
    const demoPath = path.resolve(process.cwd(), "../demo.json");
    console.error("Tried path:", demoPath);
    const raw = fs.readFileSync(demoPath, "utf-8");
    return JSON.parse(raw);
  } catch (err) {
    console.error("Failed to load demo.json:", err);
    return [];
  }
}

const demoData = loadDemoData();

// Utility functions to filter demo data by type
export function getIssuesContributorsAndClosures() {
  const issues = demoData.filter(item => item.type === "issue");
  const contributors = Array.from(new Set(issues.map(issue => issue.author)));
  const closureReasons = Array.from(new Set(issues.map(issue => issue.closure_reason)));
  return { issues, contributors, closureReasons };
}
export function getIssuesAndPRsContributorsAndClosures() {
  const allItems = demoData.filter(item => item.type === "pull_request");;
  const contributors = Array.from(new Set(allItems.map(item => item.author)));
  const closureReasons = Array.from(new Set(allItems.map(item => item.closure_reason)));
  return { allItems, contributors, closureReasons };
}

export function getContributors() {
  const map = new Map<string, {
    author: string,
    count: number,
    relevanceScores: number[],
    prs: number,
    closedPrs: number,
    completedPrs: number,
    issues: number,
    closedIssues: number,
    badItems: number // count of spam/invalid/wontfix
  }>();

  demoData.forEach(item => {
    if (!map.has(item.author)) {
      map.set(item.author, {
        author: item.author,
        count: 1,
        relevanceScores: [item.relevance_score || 0],
        prs: item.type === "pull_request" ? 1 : 0,
        closedPrs: item.type === "pull_request" && item.state === "closed" ? 1 : 0,
        completedPrs: item.type === "pull_request" && item.state === "closed" && item.closure_reason === "completed" ? 1 : 0,
        issues: item.type === "issue" ? 1 : 0,
        closedIssues: item.type === "issue" && item.state === "closed" ? 1 : 0,
        badItems: ["spam", "invalid", "wontfix"].includes(item.closure_reason) ? 1 : 0
      });
    } else {
      const contributor = map.get(item.author)!;
      contributor.count += 1;
      contributor.relevanceScores.push(item.relevance_score || 0);
      if (item.type === "pull_request") contributor.prs += 1;
      if (item.type === "pull_request" && item.state === "closed") contributor.closedPrs += 1;
      if (item.type === "pull_request" && item.state === "closed" && item.closure_reason === "completed") contributor.completedPrs += 1;
      if (item.type === "issue") contributor.issues += 1;
      if (item.type === "issue" && item.state === "closed") contributor.closedIssues += 1;
      if (["spam", "invalid", "wontfix"].includes(item.closure_reason)) contributor.badItems += 1;
    }
  });

  // Penalize contributors with more bad PRs/issues
  const contributors = Array.from(map.values()).map(c => {
    const sum = c.relevanceScores.reduce((a, b) => a + b, 0);
    const avgRelevance = c.relevanceScores.length ? sum / c.relevanceScores.length : 0;
    // Weighted score: completedPrs * avgRelevance * log(count + 1) - penalty for bad items
    const completedWeight = 5;
    const closedPrWeight = 2;
    const issueWeight = 1;
    const penaltySpam = c.badItems * 10;
    const penaltyOther = c.closedPrs - c.completedPrs - c.badItems > 0
      ? (c.badItems) * 5
      : 0;

    const weightedScore = 
      Math.round(
        (c.completedPrs * completedWeight +
        Math.log2(c.closedPrs + 1) * closedPrWeight +
        Math.log2(c.issues + 1) * issueWeight) *
        avgRelevance *
        Math.log2(c.count + 1) -
        Math.log2(c.badItems + 1) * 10 - penaltyOther - penaltySpam // logarithmic penalty for bad items
      )
  
    return {
      author: c.author,
      count: c.count,
      avgRelevance: Math.round(avgRelevance),
      weightedScore,
      completedPrs: c.completedPrs,
      closedPrs: c.closedPrs,
      prs: c.prs,
      issues: c.issues,
      closedIssues: c.closedIssues,
      badItems: c.badItems
    };
  });

  return contributors.sort((a, b) => b.weightedScore - a.weightedScore);
}

export function getRepositories() {
  // If you have repository info in demo.json, filter/group here
  return [];
}

export function getOrganizations() {
  // If you have organization info in demo.json, filter/group here
  return [];
}

// Extra: handle edge cases for missing/invalid data
export function getValidIssues() {
  return getIssuesContributorsAndClosures().issues.filter(issue =>
    issue.summary && issue.summary !== "N/A" &&
    issue.difference_analysis && issue.difference_analysis !== "N/A"
  );
}

export function getValidPullRequests() {
  return getPullRequests().filter(pr =>
    pr.summary && pr.summary !== "N/A" &&
    pr.difference_analysis && pr.difference_analysis !== "N/A"
  );
}

// You can add more filters or validators as needed for your dashboard views.