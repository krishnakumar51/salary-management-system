import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { formatMoney, formatNumber } from "@/lib/format";
import type { Currency } from "@/types/api";

// Validated categorical slots 1 & 2 (see docs/decisions.md). Magnitude of a single measure = slot 1.
export const SERIES = { blue: "#2a78d6", orange: "#eb6834" } as const;
const AXIS = "#667085";
const GRID = "#e4e7ec";

export function ChartCard({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Card>
      <CardHeader title={title} description={description} action={action} />
      <CardBody>{children}</CardBody>
    </Card>
  );
}

function TooltipBox({ active, label, payload, format }: {
  active?: boolean;
  label?: string;
  payload?: { name: string; value: number; color: string }[];
  format: (v: number, name: string) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-pop">
      <p className="mb-1 font-medium text-ink">{label}</p>
      {payload.map((p) => (
        <p key={p.name} className="flex items-center gap-2 text-ink-soft">
          <span className="size-2 rounded-sm" style={{ background: p.color }} />
          {p.name}: <span className="tabular font-medium text-ink">{format(p.value, p.name)}</span>
        </p>
      ))}
    </div>
  );
}

/** Horizontal bars of counts, sorted by the caller. Single series => no legend; the card title names it. */
export function CountBars({ data, height }: { data: { label: string; count: number }[]; height?: number }) {
  const h = height ?? Math.max(160, data.length * 32 + 24);
  return (
    <div role="img" aria-label="Bar chart of employee counts" style={{ height: h }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }} barCategoryGap={6}>
          <CartesianGrid horizontal={false} stroke={GRID} />
          <XAxis type="number" tick={{ fill: AXIS, fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
          <YAxis type="category" dataKey="label" width={118} tick={{ fill: AXIS, fontSize: 12 }} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: "#f2f4f7" }} content={<TooltipBox format={(v) => formatNumber(v)} />} />
          <Bar dataKey="count" name="Employees" fill={SERIES.blue} radius={[0, 4, 4, 0]} maxBarSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Vertical column chart of counts per salary band. */
export function BandColumns({ data, name = "Employees" }: { data: { label: string; count: number }[]; name?: string }) {
  return (
    <div role="img" aria-label="Column chart of employees per salary band" style={{ height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }} barCategoryGap={8}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="label" tick={{ fill: AXIS, fontSize: 11 }} tickLine={false} axisLine={{ stroke: GRID }} interval={0} />
          <YAxis tick={{ fill: AXIS, fontSize: 11 }} tickLine={false} axisLine={false} width={44} allowDecimals={false} />
          <Tooltip cursor={{ fill: "#f2f4f7" }} content={<TooltipBox format={(v) => formatNumber(v)} />} />
          <Bar dataKey="count" name={name} fill={SERIES.blue} radius={[4, 4, 0, 0]} maxBarSize={44} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Average vs median per group, in the reporting currency (2 series => legend present). */
export function AvgMedianBars({
  data,
  currency,
  height,
}: {
  data: { label: string; average: number; median: number }[];
  currency: Currency;
  height?: number;
}) {
  const h = height ?? Math.max(220, data.length * 44 + 40);
  return (
    <div role="img" aria-label="Bar chart of average and median compensation" style={{ height: h }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }} barGap={2} barCategoryGap={10}>
          <CartesianGrid horizontal={false} stroke={GRID} />
          <XAxis
            type="number"
            tick={{ fill: AXIS, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => formatMoney(v, currency, { compact: true })}
          />
          <YAxis type="category" dataKey="label" width={118} tick={{ fill: AXIS, fontSize: 12 }} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: "#f2f4f7" }} content={<TooltipBox format={(v) => formatMoney(v, currency)} />} />
          <Legend iconType="square" iconSize={10} wrapperStyle={{ fontSize: 12, color: AXIS }} />
          <Bar dataKey="average" name="Average" fill={SERIES.blue} radius={[0, 4, 4, 0]} maxBarSize={14} />
          <Bar dataKey="median" name="Median" fill={SERIES.orange} radius={[0, 4, 4, 0]} maxBarSize={14} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SimpleLine({
  data,
  dataKey,
  name,
  format,
  tickFormat,
}: {
  data: { label: string; value: number | null }[];
  dataKey?: string;
  name: string;
  format: (v: number) => string;
  tickFormat?: (v: number) => string;
}) {
  return (
    <div role="img" aria-label={`Line chart of ${name}`} style={{ height: 240 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="label" tick={{ fill: AXIS, fontSize: 11 }} tickLine={false} axisLine={{ stroke: GRID }} minTickGap={24} />
          <YAxis tick={{ fill: AXIS, fontSize: 11 }} tickLine={false} axisLine={false} width={52} tickFormatter={tickFormat} />
          <Tooltip content={<TooltipBox format={(v) => format(v)} />} />
          <Line
            type="monotone"
            dataKey={dataKey ?? "value"}
            name={name}
            stroke={SERIES.blue}
            strokeWidth={2}
            dot={{ r: 3, fill: SERIES.blue, stroke: "#fff", strokeWidth: 2 }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
