/**
 * PieChart - Recharts-based pie/donut chart with legend
 *
 * @module shared/components/charts
 * @template none
 * @reference none
 */
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { chartTheme } from '@/features/shared/config/chart-theme';

export interface PieChartDataItem {
  name: string;
  value: number;
}

export interface PieChartProps {
  /** 图表数据数组 */
  data: PieChartDataItem[];
  /** 图表标题 */
  title?: string;
  /** 数据来源说明 */
  source?: string;
  /** 图表高度 */
  height?: number;
  /** 是否显示标签 */
  showLabel?: boolean;
}

const RADIAN = Math.PI / 180;

interface LabelProps {
  cx?: number;
  cy?: number;
  midAngle?: number;
  innerRadius?: number;
  outerRadius?: number;
  percent?: number;
}

const renderCustomizedLabel = ({
  cx = 0,
  cy = 0,
  midAngle = 0,
  innerRadius = 0,
  outerRadius = 0,
  percent = 0,
}: LabelProps) => {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  if (percent < 0.05) return null; // 不显示小于 5% 的标签

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      fontSize={chartTheme.fonts.size.small}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

export function PieChart({
  data,
  title,
  source,
  height = chartTheme.chart.height,
  showLabel = true,
}: PieChartProps) {
  return (
    <div className="w-full">
      {title && (
        <h3 className="text-lg font-medium mb-2 text-foreground">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsPieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={showLabel ? renderCustomizedLabel : undefined}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
            nameKey="name"
          >
            {data.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={chartTheme.seriesColors[index % chartTheme.seriesColors.length]}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: chartTheme.colors.background,
              border: `1px solid ${chartTheme.colors.grid}`,
              borderRadius: '6px',
              fontSize: chartTheme.fonts.size.normal,
            }}
            formatter={(value) => [(value as number).toLocaleString(), '']}
          />
          <Legend
            wrapperStyle={{ fontSize: chartTheme.fonts.size.normal }}
          />
        </RechartsPieChart>
      </ResponsiveContainer>
      {source && (
        <p className="text-xs text-muted-foreground mt-2">
          Source: {source}
        </p>
      )}
    </div>
  );
}
