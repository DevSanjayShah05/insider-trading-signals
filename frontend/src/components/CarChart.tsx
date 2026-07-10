import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import type { CarPoint } from "../types";
import { fmtDate, fmtPct } from "../format";

interface TooltipPayloadItem {
  dataKey: string;
  value: number;
}

interface TooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

const SERIES = [
  { key: "ticker_return", name: "Ticker cumulative return", color: "var(--s-ticker)" },
  { key: "benchmark_return", name: "SPY cumulative return", color: "var(--s-benchmark)" },
  { key: "abnormal_return", name: "Abnormal return (alpha)", color: "var(--s-abnormal)" },
];

function CarTip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rc-tip">
      <div className="t-date">{fmtDate(label)}</div>
      {SERIES.map((s) => {
        const item = payload.find((p) => p.dataKey === s.key);
        if (!item) return null;
        return (
          <div className="t-row" key={s.key}>
            <span className="swatch" style={{ background: s.color }} />
            <span className="t-name">{s.name}</span>
            <span className="t-val">{fmtPct(item.value)}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function CarChart({ series, height = 280 }: { series: CarPoint[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={series} margin={{ top: 8, right: 14, left: -6, bottom: 0 }}>
        <CartesianGrid stroke="var(--grid)" strokeDasharray="2 4" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={(d: string) => fmtDate(d).replace(/, \d{4}$/, "")}
          stroke="var(--muted)"
          tick={{ fill: "var(--muted)", fontSize: 10.5, fontFamily: "var(--mono)" }}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          stroke="var(--muted)"
          tick={{ fill: "var(--muted)", fontSize: 10.5, fontFamily: "var(--mono)" }}
          tickLine={false}
          width={46}
        />
        <ReferenceLine y={0} stroke="var(--border-strong)" />
        <Tooltip content={<CarTip />} cursor={{ stroke: "var(--muted)", strokeDasharray: "3 3" }} />
        <Legend
          verticalAlign="top"
          height={28}
          formatter={(value: string) => <span style={{ color: "var(--ink-2)", fontSize: 11.5 }}>{value}</span>}
        />
        {SERIES.map((s) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={s.color}
            strokeWidth={s.key === "abnormal_return" ? 2.5 : 1.75}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
