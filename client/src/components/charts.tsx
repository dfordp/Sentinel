"use client"

import { ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts"

export function IssueCategoryPie() {
  const data = [
    { name: "Bug", value: 8, color: "var(--color-chart-1)" },
    { name: "Feature", value: 5, color: "var(--color-chart-2)" },
    { name: "Docs", value: 3, color: "var(--color-chart-3)" },
    { name: "Chore", value: 2, color: "var(--color-chart-4)" },
    { name: "Other", value: 1, color: "var(--color-chart-5)" },
  ]
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" outerRadius={80}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function ContributorReputationBar() {
  const data = [
    { name: "alice", score: 92 },
    { name: "bob", score: 75 },
    { name: "cora", score: 66 },
    { name: "dan", score: 58 },
    { name: "erin", score: 52 },
  ]
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="score" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
