/**
 * ChartContainer - Responsive chart wrapper with title, toolbar, and export support
 *
 * @module shared/components/charts
 * @template none
 * @reference none
 */
import { useRef } from 'react';
import { LineChart } from './line-chart';
import { BarChart } from './bar-chart';
import { PieChart, type PieChartDataItem } from './pie-chart';
import { ChartExport } from './chart-export';
import { Card, CardContent, CardHeader, CardTitle } from '@/features/shared/components/ui/card';

/** 图表数据类型 */
export type ChartType = 'line' | 'bar' | 'pie';

/** 图表数据结构 */
export interface ChartData {
  /** 图表类型 */
  type: ChartType;
  /** 图表标题 */
  title?: string;
  /** X 轴数据键名 */
  xKey?: string;
  /** Y 轴数据键名数组 */
  yKeys?: string[];
  /** 图表数据 */
  data: Array<Record<string, unknown>> | PieChartDataItem[];
  /** 是否堆叠（仅柱状图） */
  stacked?: boolean;
}

/** 来源引用 */
export interface SourceReference {
  document_id: string;
  document_name: string;
  page_number?: number;
}

export interface ChartContainerProps {
  /** 图表数据 */
  chart: ChartData;
  /** 来源引用列表 */
  sources?: SourceReference[];
  /** 是否显示导出按钮 */
  showExport?: boolean;
}

export function ChartContainer({
  chart,
  sources = [],
  showExport = true,
}: ChartContainerProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);

  // 构建来源文本
  const sourceText = sources.length > 0
    ? sources
        .map((s) =>
          s.page_number
            ? `${s.document_name} (p.${s.page_number})`
            : s.document_name
        )
        .join(', ')
    : undefined;

  const renderChart = () => {
    switch (chart.type) {
      case 'line':
        return (
          <LineChart
            data={chart.data as Array<Record<string, unknown>>}
            xKey={chart.xKey || 'x'}
            yKeys={chart.yKeys || ['value']}
            source={sourceText}
          />
        );
      case 'bar':
        return (
          <BarChart
            data={chart.data as Array<Record<string, unknown>>}
            xKey={chart.xKey || 'x'}
            yKeys={chart.yKeys || ['value']}
            source={sourceText}
            stacked={chart.stacked}
          />
        );
      case 'pie':
        return (
          <PieChart
            data={chart.data as PieChartDataItem[]}
            source={sourceText}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Card className="mt-4">
      {chart.title && (
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{chart.title}</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        <div ref={chartRef} className="bg-background p-4 rounded-lg">
          {renderChart()}
        </div>
        {showExport && (
          <ChartExport
            chartRef={chartRef}
            filename={`chart-${chart.type}-${Date.now()}`}
          />
        )}
      </CardContent>
    </Card>
  );
}
