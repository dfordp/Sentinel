"use client"

import { ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts"

export function IssueCategoryPie({ data = [] }: { data?: { name: string; value: number; color: string }[] }) {
  const chartData = data.length > 0 ? data : [
    { name: "No Data", value: 1, color: "var(--color-chart-1)" }
  ];
  
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={chartData} dataKey="value" nameKey="name" outerRadius={80}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip 
          contentStyle={{ 
            backgroundColor: "white",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px",
            color: "#ffffff"
            
          }}
          labelStyle={{ color: "#ffffff" }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function ContributorReputationBar({ data }: { data: { name: string; score: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <XAxis 
          dataKey="name" 
          stroke="#ffffff"
          tick={{ fill: "#ffffff" }}
        />
        <YAxis 
          stroke="#ffffff"
          tick={{ fill: "#ffffff" }}
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: "#000000",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px",
            color: "#ffffff"
          }}
          labelStyle={{ color: "#ffffff" }}
        />
        <Bar dataKey="score" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}