import React from 'react';
import { WidgetConfig, SUPPORTED_VISUALIZATIONS } from './WidgetRegistry';
import { GripHorizontal, Trash2 } from 'lucide-react';

interface WidgetWrapperProps {
  widget: WidgetConfig;
  isEditing: boolean;
  onRemove?: (id: string) => void;
  onUpdateConfig?: (id: string, newConfig: any) => void;
  onUpdateSize?: (id: string, newSize: 'small' | 'medium' | 'large' | 'full') => void;
  children: React.ReactNode;
}

export default function WidgetWrapper({ widget, isEditing, onRemove, onUpdateConfig, children }: WidgetWrapperProps) {
  const handleConfigChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (onUpdateConfig) {
      onUpdateConfig(widget.id, { ...widget.config, visualization_type: e.target.value });
    }
  };

  const supportedVis = SUPPORTED_VISUALIZATIONS[widget.type];

  return (
    <div 
      className={`bg-white dark:bg-slate-900 border ${isEditing ? 'border-blue-400 dark:border-blue-600 border-dashed' : 'border-slate-200 dark:border-slate-800'} rounded-2xl shadow-sm overflow-hidden flex flex-col relative group transition-colors h-full w-full`}
    >
      {isEditing && (
        <div className="absolute top-0 inset-x-0 z-10 flex justify-between items-center p-2 bg-slate-100/90 dark:bg-slate-800/90 backdrop-blur border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center space-x-2">
            <div className="cursor-grab active:cursor-grabbing p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded drag-handle">
              <GripHorizontal className="w-4 h-4 text-slate-500" />
            </div>
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300 font-mono">{widget.type}</span>
          </div>
          <div className="flex items-center space-x-2">
            {supportedVis && supportedVis.length > 0 && (
              <select 
                className="text-[10px] border rounded px-2 py-1 bg-white dark:bg-slate-900 dark:border-slate-600 dark:text-white"
                value={widget.config.visualization_type || supportedVis[0]}
                onChange={handleConfigChange}
                onMouseDown={e => e.stopPropagation()} // Prevent RGL from dragging on select
              >
                {supportedVis.map(v => <option key={v} value={v}>{v.toUpperCase()}</option>)}
              </select>
            )}
            <button 
              onMouseDown={e => e.stopPropagation()}
              onClick={() => onRemove && onRemove(widget.id)} 
              className="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
      <div className={`flex-1 overflow-auto ${isEditing ? 'mt-10 pointer-events-none' : ''}`}>
        {children}
      </div>
    </div>
  );
}
