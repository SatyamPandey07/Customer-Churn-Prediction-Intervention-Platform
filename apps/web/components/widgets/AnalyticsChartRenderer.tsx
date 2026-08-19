import React, { useRef } from 'react';
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, Legend } from 'recharts';
import { Download } from 'lucide-react';

export type VisualizationType = 'bar' | 'pie' | 'line' | 'stat' | 'table';

export interface ChartConfig {
  visualization_type: VisualizationType;
  xAxisKey?: string;
  dataKeys: string[];
  colors?: string[];
  time_range?: '7d' | '30d' | '90d' | 'ytd' | 'all';
  granularity?: 'daily' | 'weekly' | 'monthly';
}

interface Props {
  data: any[];
  config: ChartConfig;
  title?: string;
}

const DEFAULT_COLORS = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444'];

export default function AnalyticsChartRenderer({ data, config, title }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);

  const handleExportCSV = () => {
    if (!data || data.length === 0) return;
    const keys = Object.keys(data[0]);
    const csvContent = [
      keys.join(','),
      ...data.map(row => keys.map(k => JSON.stringify(row[k])).join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', `${title || 'export'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportImage = () => {
    if (!chartRef.current) return;
    const svgElement = chartRef.current.querySelector('svg');
    if (!svgElement) return;

    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svgElement);
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `${title || 'chart'}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Mock data aggregation based on config
  let renderData = [...data];
  if (config.granularity === 'monthly' && renderData.length > 0 && renderData[0].date) {
    // Naive mock bucketing for demo
    renderData = renderData.filter((_, i) => i % 30 === 0);
  } else if (config.granularity === 'weekly' && renderData.length > 0 && renderData[0].date) {
    renderData = renderData.filter((_, i) => i % 7 === 0);
  }

  if (config.time_range === '7d') renderData = renderData.slice(-7);
  else if (config.time_range === '30d') renderData = renderData.slice(-30);

  const renderChart = () => {
    switch (config.visualization_type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={renderData}>
              <XAxis dataKey={config.xAxisKey || 'name'} stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff', borderRadius: '0.75rem', fontSize: '12px' }} />
              <Legend />
              {config.dataKeys.map((key, idx) => (
                <Bar key={key} dataKey={key} fill={config.colors?.[idx] || DEFAULT_COLORS[idx % DEFAULT_COLORS.length]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );
      case 'line':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={renderData}>
              <XAxis dataKey={config.xAxisKey || 'name'} stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff', borderRadius: '0.75rem', fontSize: '12px' }} />
              <Legend />
              {config.dataKeys.map((key, idx) => (
                <Line key={key} type="monotone" dataKey={key} stroke={config.colors?.[idx] || DEFAULT_COLORS[idx % DEFAULT_COLORS.length]} strokeWidth={2} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );
      case 'pie':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={renderData} dataKey={config.dataKeys[0]} nameKey={config.xAxisKey || 'name'} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5}>
                {renderData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={config.colors?.[index] || entry.fill || DEFAULT_COLORS[index % DEFAULT_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff', borderRadius: '0.75rem', fontSize: '12px' }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );
      case 'table':
        return (
          <div className="overflow-x-auto w-full h-full">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold text-slate-500 uppercase">
                  <th className="py-2 px-3">{config.xAxisKey || 'Name'}</th>
                  {config.dataKeys.map(key => <th key={key} className="py-2 px-3">{key}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {renderData.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="py-2 px-3 font-semibold text-slate-900 dark:text-slate-200">{row[config.xAxisKey || 'name'] || row.name || `Row ${idx}`}</td>
                    {config.dataKeys.map(key => <td key={key} className="py-2 px-3 text-slate-700 dark:text-slate-300">{row[key]}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      case 'stat':
        return (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-4xl font-extrabold text-slate-900 dark:text-white">
              {renderData.reduce((sum, row) => sum + (row[config.dataKeys[0]] || 0), 0).toLocaleString()}
            </div>
            <div className="text-sm text-slate-500 font-semibold mt-1">Total {config.dataKeys[0]}</div>
          </div>
        );
      default:
        return <div>Unsupported visualization type</div>;
    }
  };

  return (
    <div className="w-full h-full flex flex-col group">
      <div className="flex justify-between items-center mb-4">
        {title && <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">{title}</h3>}
        <div className="flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={handleExportCSV} className="p-1 text-slate-500 hover:text-blue-600 rounded bg-slate-100 dark:bg-slate-800" title="Export CSV">
            <span className="text-[10px] font-bold px-1">CSV</span>
          </button>
          <button onClick={handleExportImage} className="p-1 text-slate-500 hover:text-blue-600 rounded bg-slate-100 dark:bg-slate-800" title="Export Image">
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      <div className="flex-1 min-h-[200px]" ref={chartRef}>
        {renderChart()}
      </div>
    </div>
  );
}
