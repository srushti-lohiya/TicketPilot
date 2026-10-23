"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { humanize } from "@/lib/utils";
import { Empty } from "./common";
const colors = ["#6366f1", "#a5b4fc", "#34b5a0", "#cbd5e1", "#818cf8"];
export function DistributionChart({
  values,
  percentage = false,
}: {
  values: Record<string, number>;
  percentage?: boolean;
}) {
  const rows = Object.entries(values).map(([key, value]) => ({
    name: humanize(key),
    value: percentage ? value * 100 : value,
  }));
  if (!rows.length || rows.every((r) => r.value === 0))
    return (
      <Empty
        title="No chart data yet"
        description="Distributions appear after tickets have been processed."
      />
    );
  return (
    <div
      className="h-64 w-full px-4 pt-6 pb-3"
      role="img"
      aria-label={rows
        .map(
          (r) =>
            `${r.name}: ${r.value.toFixed(percentage ? 1 : 0)}${percentage ? "%" : ""}`,
        )
        .join(", ")}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ left: 0, right: 24, top: 0, bottom: 0 }}
          barSize={16}
        >
          <CartesianGrid horizontal={false} stroke="#f1f5f9" />
          <XAxis
            type="number"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            allowDecimals={percentage}
            domain={percentage ? [0, 100] : [0, "auto"]}
            unit={percentage ? "%" : undefined}
          />
          <YAxis
            type="category"
            dataKey="name"
            axisLine={false}
            tickLine={false}
            width={128}
            tick={{ fill: "#64748b", fontSize: 11 }}
          />
          <Tooltip
            cursor={{ fill: "#f8fafc" }}
            contentStyle={{
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              color: "#0f172a",
              fontSize: 12,
            }}
            formatter={(value) => [
              percentage
                ? `${Number(value).toFixed(1)}%`
                : Number(value).toLocaleString(),
              percentage ? "Rate" : "Tickets",
            ]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive={false}>
            {rows.map((r, i) => (
              <Cell key={r.name} fill={colors[i % colors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
