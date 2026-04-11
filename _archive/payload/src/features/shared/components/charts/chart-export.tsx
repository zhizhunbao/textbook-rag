/**
 * ChartExport - Chart export utilities for PNG and PDF formats
 *
 * @module shared/components/charts
 * @template none
 * @reference none
 */
import { type RefObject } from 'react';
import { toPng } from 'html-to-image';
import { jsPDF } from 'jspdf';
import { Download, FileText } from 'lucide-react';
import { Button } from '@/features/shared/components/ui/button';

export interface ChartExportProps {
  /** 图表容器的 ref */
  chartRef: RefObject<HTMLDivElement | null>;
  /** 导出文件名（不含扩展名） */
  filename?: string;
  /** 是否显示标签文字 */
  showLabels?: boolean;
}

export function ChartExport({
  chartRef,
  filename = 'chart',
  showLabels = true,
}: ChartExportProps) {
  const exportAsPng = async () => {
    if (!chartRef.current) return;

    try {
      const dataUrl = await toPng(chartRef.current, {
        quality: 0.95,
        backgroundColor: '#ffffff',
      });
      const link = document.createElement('a');
      link.download = `${filename}.png`;
      link.href = dataUrl;
      link.click();
    } catch (error) {
      console.error('Failed to export chart as PNG:', error);
    }
  };

  const exportAsPdf = async () => {
    if (!chartRef.current) return;

    try {
      const dataUrl = await toPng(chartRef.current, {
        quality: 0.95,
        backgroundColor: '#ffffff',
      });
      const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'px',
      });
      const imgProps = pdf.getImageProperties(dataUrl);
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;

      // 居中放置图片
      const x = 0;
      const y = (pdf.internal.pageSize.getHeight() - pdfHeight) / 2;

      pdf.addImage(dataUrl, 'PNG', x, y, pdfWidth, pdfHeight);
      pdf.save(`${filename}.pdf`);
    } catch (error) {
      console.error('Failed to export chart as PDF:', error);
    }
  };

  return (
    <div className="flex gap-2 mt-3">
      <Button variant="outline" size="sm" onClick={exportAsPng}>
        <Download className="h-4 w-4" />
        {showLabels && <span className="ml-1">PNG</span>}
      </Button>
      <Button variant="outline" size="sm" onClick={exportAsPdf}>
        <FileText className="h-4 w-4" />
        {showLabels && <span className="ml-1">PDF</span>}
      </Button>
    </div>
  );
}
