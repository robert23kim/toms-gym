import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface WeekData {
  week_start_date: string;
  label: string;
  lifts: Record<string, number>;
  total: number;
}

interface WeeklyLiftsChartProps {
  weeks: WeekData[];
}

const LIFT_COLORS: Record<string, string> = {
  bench: '#ef4444',       // red
  squat: '#3b82f6',       // blue
  deadlift: '#22c55e',    // green
  sitting_press: '#f59e0b', // amber
};

const LIFT_LABELS: Record<string, string> = {
  bench: 'Bench Press',
  squat: 'Squat',
  deadlift: 'Deadlift',
  sitting_press: 'Sitting Press',
};

const WeeklyLiftsChart: React.FC<WeeklyLiftsChartProps> = ({ weeks }) => {
  // Sort weeks chronologically for the chart (oldest to newest)
  const sortedWeeks = [...weeks].sort((a, b) =>
    new Date(a.week_start_date).getTime() - new Date(b.week_start_date).getTime()
  );

  // Transform data for Recharts
  const chartData = sortedWeeks.map((week) => ({
    name: week.label,
    date: week.week_start_date,
    bench: week.lifts.bench || null,
    squat: week.lifts.squat || null,
    deadlift: week.lifts.deadlift || null,
    sitting_press: week.lifts.sitting_press || null,
  }));

  // Determine which lift types have data
  const activeLiftTypes = Object.keys(LIFT_COLORS).filter((liftType) =>
    chartData.some((week) => week[liftType as keyof typeof week] !== null)
  );

  if (weeks.length === 0) {
    return (
      <div className="bg-card rounded-xl p-4 shadow-sm">
        <h3 className="text-lg font-semibold mb-4">Progress Over Time</h3>
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          Add weekly lifts to see your progress chart
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Progress Over Time</h3>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
              label={{ value: 'Weight (lbs)', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                borderColor: 'hsl(var(--border))',
                borderRadius: '8px',
              }}
              labelStyle={{ fontWeight: 'bold' }}
              formatter={(value: number, name: string) => [
                `${value} lbs`,
                LIFT_LABELS[name] || name,
              ]}
            />
            <Legend
              formatter={(value: string) => LIFT_LABELS[value] || value}
            />
            {activeLiftTypes.map((liftType) => (
              <Line
                key={liftType}
                type="monotone"
                dataKey={liftType}
                stroke={LIFT_COLORS[liftType]}
                strokeWidth={2}
                dot={{ fill: LIFT_COLORS[liftType], strokeWidth: 2 }}
                activeDot={{ r: 6 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default WeeklyLiftsChart;
