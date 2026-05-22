import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
  Tooltip,
} from 'recharts';

const COLORS = {
  木: '#34C759',
  火: '#FF3B30',
  土: '#C68C53',
  金: '#A1A1A6',
  水: '#4A6FFF',
};

export default function OhengChart({ data }) {
  const chartData = Object.entries(data || {}).map(([key, value]) => ({
    name: key,
    value,
    fill: COLORS[key] || '#888',
  }));

  return (
    <div className="w-full h-56">
      <ResponsiveContainer>
        <BarChart data={chartData}>
          <XAxis
            dataKey="name"
            tick={{ fontSize: 16, fontWeight: 700 }}
            stroke="#6E6E73"
          />
          <YAxis hide domain={[0, 'dataMax + 1']} />
          <Tooltip
            cursor={{ fill: 'rgba(0,0,0,0.04)' }}
            contentStyle={{
              borderRadius: 12,
              border: '1px solid rgba(0,0,0,0.08)',
              fontSize: 13,
            }}
          />
          <Bar dataKey="value" radius={[8, 8, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
