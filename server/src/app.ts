import express from "express";
import cors from "cors";
import axios from "axios";
import { Pool } from "pg";
import OpenAI from "openai";
import pgvector from "pgvector/pg";
import fs from "fs";
import { Groq } from 'groq-sdk';
import { log } from "console";

const groq = new Groq({
  apiKey : process.env.GROQ_API_KEY,
});


const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});


const pool = new Pool({
  host: "localhost",
  port: 5432,
  user: "postgres",
  password: "yourpassword",
  database: "postgres"
});

pool.on('connect', async function (client) {
  await pgvector.registerTypes(client);
});


const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const OWNER = process.env.OWNER;
const REPO = process.env.REPO;

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static("public"))
app.use(express.urlencoded({extended: true}));



app.get("/", (req, res) => {
    res.send({message: "Hello From Sentinal API"});
});


app.get("/repo/items-full", async (req, res) => {
  try {
    const response = await axios.get(
      `https://api.github.com/repos/${OWNER}/${REPO}/issues?state=all&per_page=100`,
      {
        headers: {
          Authorization: `Bearer ${GITHUB_TOKEN}`,
          Accept: "application/vnd.github.v3+json"
        }
      }
    );
    const items = await Promise.all(
      response.data.map(async item => {
        const type = item.pull_request ? "pull_request" : "issue";
        // Fetch comments
        const comments = await axios.get(item.comments_url, {
          headers: {
            Authorization: `Bearer ${GITHUB_TOKEN}`,
            Accept: "application/vnd.github.v3+json"
          }
        });
        // Fetch timeline events (full history)
        const timeline = await axios.get(item.timeline_url, {
          headers: {
            Authorization: `Bearer ${GITHUB_TOKEN}`,
            Accept: "application/vnd.github.v3+json"
          }
        });
        return {
          ...item,
          type,
          comments: comments.data,
          timeline: timeline.data,
        };
      })
    );
    res.json(items);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    res.status(500).json({ error: "Failed to fetch issues/PRs and their threads", details: errorMessage });
  }
});

function extractKeywords(text) {
  if (!text) return [];
  return [...new Set(
    text
      .toLowerCase()
      .replace(/[.,\/#!$%^&*;:{}=\-_`~()]/g,"")
      .split(/\s+/)
      .filter(w => w.length > 3)
  )];
}

function isStale(item) {
  const THIRTY_DAYS = 1000 * 60 * 60 * 24 * 30;
  const updated = new Date(item.updated_at).getTime();
  return item.state === "open" && Date.now() - updated > THIRTY_DAYS;
}

function isSpam(item) {
  const spamWords = ["free", "click", "visit", "promo", "subscribe", "bitch"];
  const text = `${item.title || ""} ${item.body || ""}`.toLowerCase();
  return spamWords.some(sw => text.includes(sw));
}


async function computeEmbedding(keywords) {
  const input = Array.isArray(keywords) ? keywords.join(" ") : String(keywords);

  const response = await openai.embeddings.create({
    model: "text-embedding-3-small", // or "text-embedding-3-large"
    input,
    encoding_format: "float",
  });

  // response.data[0].embedding will be the embedding vector
  return response.data[0].embedding;
}

function extractFileUrls(text) {
  if (!text) return [];
  // Simple regex for Markdown/image/file links
  const urlRegex = /(https?:\/\/[^\s)]+)/g;
  return text.match(urlRegex) || [];
}

function summarizeDiff(diffText: string): string {
  // TODO: Implement a real diff summarizer, or use an LLM for this
  // For now, just return the first 500 characters as a summary
  return diffText ? diffText.slice(0, 500) + (diffText.length > 500 ? '...' : '') : '';
}

app.get("/repo/keywords", async (req, res) => {
  try {
    const response = await axios.get(
      `https://api.github.com/repos/${OWNER}/${REPO}/issues?state=all&per_page=100`,
      { headers: { Authorization: `Bearer ${GITHUB_TOKEN}`, Accept: "application/vnd.github.v3+json" } }
    );
    const items = await Promise.all(
      response.data.map(async item => {
        // 1. Fetch all comments
        const comments = await axios.get(item.comments_url, {
          headers: {
            Authorization: `Bearer ${GITHUB_TOKEN}`,
            Accept: "application/vnd.github.v3+json"
          }
        });
        const commentsArray = comments.data ? comments.data.map(c => c.body) : [];

        const type = item.pull_request ? "pull_request" : "issue";
        const allText = [
          item.title,
          item.body,
          ...(item.labels ? item.labels.map(l => l.name) : []),
          ...commentsArray
        ].join(' ');
        const keywords = extractKeywords(allText);
        const embedding = await computeEmbedding(keywords);

        if (!embedding || !Array.isArray(embedding) || embedding.length === 0) {
          throw new Error("Embedding is empty or invalid");
        }

        const related = (item.body || "").match(/#\d+/g) || [];
        const matchesRequirements = (item.body || "").toLowerCase().includes('checklist');

        const fileUrls = [
        ...extractFileUrls(item.body),
        ...(Array.isArray(item.comments) ? item.comments.flatMap(extractFileUrls) : [])
      ];
      // For PRs, fetch and summarize the diff
      let diffSummary = "";
      if (item.type === "pull_request" && item.pull_request?.diff_url) {
        const diffResponse = await axios.get(item.pull_request.diff_url, { headers: { Authorization: `Bearer ${GITHUB_TOKEN}` } });
        diffSummary = diffResponse.data; // Implement summarizeDiff as needed
      }


        // take into account code differences 
        // better interlinking and take into context other related issues and other issues and prs that take into account similar keywords and all 
        // take into account status of the issue and pr also as context 

        // 2. Store all fields (including comments!) in the DB
        await pool.query(
          `INSERT INTO github_items
            (id, number, type, keywords, labels, embedding, state, author, updated_at, created_at, related, is_stale, is_spam, matches_requirements, comments, title, body, file_urls, diff_summary)
          VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
          ON CONFLICT (id) DO NOTHING`,
          [
            item.id,
            item.number,
            type,
            keywords,
            item.labels?.map(l => l.name),
            pgvector.toSql(embedding),
            item.state,
            item.user?.login,
            item.updated_at,
            item.created_at,
            related,
            isStale(item),
            isSpam(item),
            matchesRequirements,
            commentsArray,
            item.title,
            item.body,
            fileUrls,
            diffSummary
          ]
        );
        return { id: item.id, keywords, embedding };
      })
    );
    fs.writeFileSync("./embeddings.json", JSON.stringify(items, null, 2));
    res.json(items);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    res.status(500).json({ error: "Failed to process keywords/embedding/DB", details: errorMessage });
  }
});


app.get("/repo/insights-reviewed", async (req, res) => {
  try {
    // Use the full schema you specified
    const { rows: items } = await pool.query(
      `SELECT 
          id, number, type, keywords, labels, embedding, state, author, updated_at, created_at, related, is_stale, is_spam, matches_requirements,
          COALESCE(comments, ARRAY[]::text[]) AS comments,
          COALESCE(title, '') AS title,
          COALESCE(body, '') AS body,
          COALESCE(file_urls, ARRAY[]::text[]) AS file_urls,
          COALESCE(diff_summary, '') AS diff_summary
      FROM github_items`
    );

    const reviewed = await Promise.all(
      items.map(async (item) => {
        // Compose all content into a context for the model
        const contextParts = [
      `Title: ${item.title ?? ""}`,
      `Body: ${item.body ?? ""}`,
      ...(Array.isArray(item.keywords) ? item.keywords : []),
      ...(Array.isArray(item.labels) ? item.labels : []),
      ...(Array.isArray(item.comments) ? item.comments : []),
      ...(Array.isArray(item.file_urls) ? item.file_urls.map(url => `File: ${url}`) : []),
      `State: ${item.state}`,
      `Author: ${item.author}`,
      `Related: ${(item.related || []).join(", ")}`,
      `is_stale: ${item.is_stale}, is_spam: ${item.is_spam}, matches_requirements: ${item.matches_requirements}`,
      // Add code diff summary if available
      item.diff_summary ? `Code Diff: ${item.diff_summary}` : "",
      // Add related issues/PRs status if available
      item.related_status ? `Related Status: ${item.related_status}` : ""
    ].filter(Boolean);

      const fullText = contextParts.join('\n\n');
      // const prompt = `You are a maintainer. Review this GitHub issue or PR and return a JSON object: {"label":"spam|stale|genuine", "summary":"...", "reason":"..."}.\n\nContent:\n${fullText}`;

      const project =`
      ## Overview

      Hackmate is a swipe-based matchmaking platform designed for founders and builders to meet potential co-founders, collaborators, and indie hackers.

      Instead of social media profiles and endless bios, Hackmate focuses on skills, intent, and mutual interest. Users create lightweight profiles, swipe to express interest, and get matched in real time if there is mutual alignment.

      The app was built to make collaboration faster and more intentional for startup ecosystems, hackathons, and builder communities.

      ---

      ## How It Works

      1. Users create a profile with their skills, experience, and goals.
      2. The app shows other profiles that can be swiped right (interested) or left (skip).
      3. When two users swipe right on each other, they instantly appear in a shared match queue.
      4. Matched users can view details and connect immediately.

      This approach removes friction from networking by focusing only on aligned intent and relevant skills.

      ---

      ## Key Features

      * **Swipe-based discovery**: Browse and evaluate potential collaborators quickly.
      * **Real-time matches**: Matches appear instantly through a Redis-backed caching layer.
      * **Mutual-only visibility**: Users only see interest if it is reciprocated, reducing pressure.
      * **Skill-focused profiles**: Profiles highlight what users can do and what they have built.
      * **Low-latency infrastructure**: Redis and WebSockets ensure fast responses for swipes and matches.

      ---

      ## Technology Stack

      **Frontend**

      * Next.js for the web application
      * Tailwind CSS for styling

      **Backend**

      * PostgreSQL for structured data
      * Redis for real-time caching and match detection

      **Infrastructure**

      * Vercel for hosting
      * Redis running locally via Docker or in the cloud (Upstash, Aiven, etc.)

      ## Redis Store Design

      | Purpose       | Type | Key Format          | Example                          |
      | ------------- | ---- | ------------------- | -------------------------------- |
      | Likes Given   | SET  | likes:<user_id>  | Used to prevent duplicate swipes |
      | Match Queue   | LIST | matches:<user_id>| Stores mutual matches            |
      | User Profiles | HASH | user:<user_id>   | Caches basic profile information |

      Other matching logic, such as filtering, exclusions, and scoring, is handled through the backend services.


      ## Future Development

      Planned features include:

      * Role and interest-based filtering (e.g., designer, product, engineering)
      * Matching based on timezone and geography
      * Project pitch cards and lightweight portfolios
      * Improved match feed and conversation prompts


      Here is a **CONTRIBUTING.md** file written in the same style as your README.md (no emojis, no AI buzzwords, no double dashes, and keeping the passion-project tone):


      # Contributing to Hackmate

      Thank you for your interest in contributing. Hackmate started as a side project to explore whether swipe-style discovery could improve how founders and builders connect. Every contribution, whether big or small, helps move the project forward.

      For Discussions Join : [Discord](https://discord.gg/E8MaEyD7ws)

      ## How to Get Started

      1. **Fork the repository** and clone your fork locally.
      2. **Set up the environment** following the steps in the README.
      3. Create a new branch for your work with a descriptive name.
      4. Make your changes in small, focused commits.
      5. Run the linter and tests before pushing.
      6. Submit a pull request against the main branch.


      ## Reporting Issues

      If you encounter a bug or want to suggest an improvement, open an issue. Please include:

      * A clear title and description.
      * Steps to reproduce the problem (if reporting a bug).
      * Expected behavior versus actual behavior.
      * Screenshots, logs, or environment details if relevant.

      For sensitive security-related issues, please do not file a public issue. Instead, reach out directly to the maintainer.

      ## Suggesting Features

      Before starting work on a new feature, open an issue to discuss the idea. This helps ensure efforts are aligned with the direction of the project. Describe:

      * The problem you are solving.
      * The proposed solution.
      * Any impact on the existing data model or flows.


      ## Code Guidelines

      * Follow existing patterns in the codebase.
      * Use TypeScript where possible to keep types clear and reduce errors.
      * Keep functions small and focused.


      ## Development Environment

      * **Frontend:** Next.js with Tailwind CSS
      * **Backend:** Prisma with PostgreSQL
      * **Real-time:** Redis for caching and match detection
      * **Auth:** Clerk
      * **Hosting:** Vercel
      `

      const prompt = `
        You are an expert open source maintainer using advanced analytics to review contributions for this project:

        ${project}

        You receive, for each contribution, full context (title, body, metadata, keywords, labels, related items, code diffs, comments, contributor history, etc.).

        Your task:
        - Read through the contribution as a maintainer.
        - Evaluate how relevant this contribution is to project goals and technical progress. Consider technical depth, code coverage, difference compared to other PRs/issues, if it fulfills missing requirements, and degree of checklist/completeness.
        - Provide a single "relevance_score" as a percentage (0-100%), indicating how useful/important this contribution is relative to the project's active needs and roadmap.
        - Thoroughly summarize technically (reference unique and overlapping aspects, list key technical details, technical novelty or overlap).
        - Evaluate what sets this item apart (or what is missing), and highlight whether it covers unique ground compared to other items.

        Return a pure JSON object in this format:
        {
          "relevance_score": 85, 
          "summary": "Technical and detailed summary highlighting contribution value and context.",
          "difference_analysis": "What makes this unique, what it overlaps with, or what it lacks.",
          "best_in_group": "true|false",
          "best_rationale": "If this is the most relevant or highest-quality item among related ones, say why and reference the context. Otherwise, explain what is missing or less relevant."
        }

        Content to review:
        ${fullText}
        `;
      

      // Call Groq chat completion
      const chatCompletion = await groq.chat.completions.create({
        messages: [
          {
            role: "user",
            content: prompt
          }
        ],
        model: "openai/gpt-oss-20b",
        temperature: 1,
        max_completion_tokens: 10000,
        top_p: 1,
        stream: false,
        reasoning_effort: "medium",
        stop: null
      });



      let result = { relevance_score: "", summary: "", difference_analysis: "", best_in_group: "", best_rationale: ""};
      let retries = 0;
      const MAX_RETRIES = 2;

      while (
        retries < MAX_RETRIES &&
        (
          !result.summary ||
          result.label === "unknown" ||
          Object.values(result).every(v => v === "" || v === "unknown")
        )
      ) {
        try {
          result = JSON.parse(chatCompletion.choices?.[0]?.message?.content?.trim() ?? "{}");
        } catch {
          // If parsing fails, keep result as default
        }
        retries++;
        // Optionally: re-call the model with a slightly modified prompt or log the attempt
        // For now, just retry parsing the same output
      }
      return {
        id: item.id,
        number: item.number,
        type: item.type,
        author: item.author,
        related: item.related,
        is_stale: item.is_stale,
        is_spam: item.is_spam,
        matches_requirements: item.matches_requirements,
        relevance_score: result.relevance_score,
        summary: result.summary,
        difference_analysis: result.difference_analysis,
        best_in_group: result.best_in_group,
        best_rationale: result.best_rationale,
      };
    })
  );
    res.json(reviewed);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    res.status(500).json({ error: "Failed to analyze with GPT-OSS", details: errorMessage });
  }
});


export const startServer = async () => {
    try {
        // if(process.env.MONGODB_URL) await connectDB(process.env.MONGODB_URL);
        app.listen(8080, () => console.log("Sentinal Api started on http://localhost:8080"));
    } catch (error) {
        console.log(error);
    }
}