"use client";

import { useEffect, useState, useRef, useCallback } from 'react';
import { useRealtime } from '@/components/RealtimeProvider';
import { 
  AlertTriangle, DollarSign, TrendingUp, Sparkles, 
  ChevronRight, X, Mail, Send, MessageSquare, CheckCircle, Undo2, Redo2
} from 'lucide-react';
import { Customer, MOCK_ANALYTICS } from '@/lib/demoData';
import { debounce } from 'lodash';

import { ResponsiveGridLayout, Layout, LayoutItem, ResponsiveLayouts as Layouts, useContainerWidth } from 'react-grid-layout';

import { WidgetConfig, WidgetType, WIDGET_DEF } from '@/components/widgets/WidgetRegistry';
import WidgetWrapper from '@/components/widgets/WidgetWrapper';
import MetricsSummaryWidget from '@/components/widgets/MetricsSummaryWidget';
import ChurnRiskTableWidget from '@/components/widgets/ChurnRiskTableWidget';
import AnalyticsWidget from '@/components/widgets/AnalyticsWidget';

interface DashboardState {
  widgets: WidgetConfig[];
  layouts: Layouts;
}

export default function ClientDashboard({ initialCustomers }: { initialCustomers: Customer[] }) {
  const { width, containerRef, mounted } = useContainerWidth();
  const [customers, setCustomers] = useState<Customer[]>(initialCustomers);
  const [dashboardData, setDashboardData] = useState<DashboardState>({ widgets: [], layouts: {} });
  const [isEditMode, setIsEditMode] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [outreachSuccess, setOutreachSuccess] = useState<string | null>(null);

  // Undo/Redo State
  const [history, setHistory] = useState<DashboardState[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const socket = useRealtime();

  useEffect(() => {
    if (!socket) return;
    const handleUpdate = (data: any) => {
      setCustomers(prev => prev.map(c => c.id === data.customer_id ? { ...c, churn_probability: data.churn_probability, churn_risk_tier: data.churn_risk_tier } : c));
    };
    socket.on('churn_update', handleUpdate);
    return () => { socket.off('churn_update', handleUpdate); };
  }, [socket]);

  useEffect(() => {
    fetch('/api/dashboard/layout')
      .then(res => res.json())
      .then(data => {
        let initialData: DashboardState;
        if (data.layout && data.layout.widgets && data.layout.widgets.length > 0) {
          initialData = data.layout;
        } else {
          // System Default fallback
          initialData = {
            widgets: [
              { id: 'default-metrics', type: WidgetType.METRICS_SUMMARY, config: {} },
              { id: 'default-table', type: WidgetType.CHURN_RISK_TABLE, config: { risk_tier_filter: 'all', row_limit: 10 } }
            ],
            layouts: {
              lg: [
                { i: 'default-metrics', x: 0, y: 0, w: 12, h: 1, minW: WIDGET_DEF[WidgetType.METRICS_SUMMARY].minW, minH: WIDGET_DEF[WidgetType.METRICS_SUMMARY].minH },
                { i: 'default-table', x: 0, y: 1, w: 12, h: 3, minW: WIDGET_DEF[WidgetType.CHURN_RISK_TABLE].minW, minH: WIDGET_DEF[WidgetType.CHURN_RISK_TABLE].minH }
              ]
            }
          };
        }
        setDashboardData(initialData);
        setHistory([initialData]);
        setHistoryIndex(0);
        setIsLoading(false);
      })
      .catch(() => setIsLoading(false));
  }, []);

  const pushHistory = useCallback((newState: DashboardState) => {
    setHistory(prev => {
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push(newState);
      setHistoryIndex(newHistory.length - 1);
      return newHistory;
    });
    setDashboardData(newState);
  }, [historyIndex]);

  const handleUndo = () => {
    if (historyIndex > 0) {
      setHistoryIndex(i => i - 1);
      setDashboardData(history[historyIndex - 1]);
      debouncedSave(history[historyIndex - 1]);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex(i => i + 1);
      setDashboardData(history[historyIndex + 1]);
      debouncedSave(history[historyIndex + 1]);
    }
  };

  const debouncedSave = useRef(
    debounce(async (dataToSave: DashboardState) => {
      try {
        await fetch('/api/dashboard/layout', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(dataToSave)
        });
      } catch (e) {
        console.error("Failed to save layout");
      }
    }, 1000)
  ).current;

  const onLayoutChange = (currentLayout: Layout, allLayouts: Layouts) => {
    // Only push to history and save if we are in edit mode
    // (react-grid-layout triggers onLayoutChange on mount and resize, which we want to ignore for history)
    if (!isEditMode) return;
    
    setDashboardData(prev => {
      // Basic deep equality check to prevent pushing duplicate history on mount/no-ops
      if (JSON.stringify(prev.layouts) === JSON.stringify(allLayouts)) {
        return prev;
      }
      const newState = { ...prev, layouts: allLayouts };
      pushHistory(newState);
      debouncedSave(newState);
      return newState;
    });
  };

  const publishTenantDefault = async () => {
    try {
      await fetch('/api/dashboard/layout/tenant-default', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dashboardData)
      });
      alert("Tenant default published successfully.");
      setIsEditMode(false);
    } catch (e) {
      alert("Failed to publish default.");
    }
  };

  const resetToDefault = async () => {
    await fetch('/api/dashboard/layout', { method: 'DELETE' });
    window.location.reload();
  };

  const addWidget = (type: WidgetType) => {
    const id = `${type}-${Date.now()}`;
    const def = WIDGET_DEF[type];
    const newWidget: WidgetConfig = { id, type, config: { ...def.defaultConfig } };
    
    // Auto-place at the bottom
    const newLayoutItem: LayoutItem = {
      i: id,
      x: 0,
      y: Infinity, // puts it at the bottom
      w: def.minW || 4,
      h: def.minH || 2,
      minW: def.minW || 2,
      minH: def.minH || 2
    };

    const newState: DashboardState = {
      widgets: [...dashboardData.widgets, newWidget],
      layouts: {
        ...dashboardData.layouts,
        lg: [...(dashboardData.layouts.lg || []), newLayoutItem]
      }
    };
    
    pushHistory(newState);
    debouncedSave(newState);
  };

  const removeWidget = (id: string) => {
    const newState: DashboardState = {
      widgets: dashboardData.widgets.filter(w => w.id !== id),
      layouts: Object.fromEntries(
        Object.entries(dashboardData.layouts).map(([bp, layout]) => [
          bp,
          (layout as Layout).filter((l: LayoutItem) => l.i !== id)
        ])
      )
    };
    pushHistory(newState);
    debouncedSave(newState);
  };

  const updateWidgetConfig = (id: string, newConfig: any) => {
    const newState: DashboardState = {
      ...dashboardData,
      widgets: dashboardData.widgets.map(w => w.id === id ? { ...w, config: newConfig } : w)
    };
    pushHistory(newState);
    debouncedSave(newState);
  };

  const totalMrrAtRisk = customers.filter(c => ['critical', 'high'].includes(c.churn_risk_tier || '')).reduce((sum, c) => sum + (c.mrr || 0), 0);
  const criticalCount = customers.filter(c => c.churn_risk_tier === 'critical').length;
  const avgRisk = customers.length > 0 ? (customers.reduce((sum, c) => sum + (c.churn_probability || 0), 0) / customers.length * 100).toFixed(1) : '0';

  if (isLoading) {
    return <div className="text-sm text-slate-500 p-8">Loading dashboard configuration...</div>;
  }

  const renderWidget = (w: WidgetConfig) => {
    switch (w.type) {
      case WidgetType.METRICS_SUMMARY:
        return <MetricsSummaryWidget totalMrrAtRisk={totalMrrAtRisk} criticalCount={criticalCount} avgRisk={avgRisk} customersCount={customers.length} />;
      case WidgetType.CHURN_RISK_TABLE:
        return <ChurnRiskTableWidget customers={customers} onSelectCustomer={setSelectedCustomer} config={w.config} />;
      case WidgetType.ANALYTICS_ROI:
      case WidgetType.ANALYTICS_INTERVENTIONS:
      case WidgetType.ANALYTICS_COHORTS:
      case WidgetType.ANALYTICS_RAR:
        return <AnalyticsWidget widgetConfig={w} analyticsData={MOCK_ANALYTICS} />;
      default:
        return <div className="p-4 text-xs text-slate-500 border border-dashed border-slate-300 rounded-lg">Unsupported Widget: {w.type}</div>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Controls Bar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">Churn Risk Dashboard</h1>
        <div className="flex flex-wrap items-center gap-3">
          {isEditMode ? (
            <>
              <div className="flex items-center space-x-1 border-r border-slate-300 dark:border-slate-700 pr-3">
                <button 
                  onClick={handleUndo} 
                  disabled={historyIndex <= 0}
                  className="p-1.5 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-30 rounded-lg"
                  title="Undo Layout Change"
                >
                  <Undo2 className="w-4 h-4" />
                </button>
                <button 
                  onClick={handleRedo} 
                  disabled={historyIndex >= history.length - 1}
                  className="p-1.5 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-30 rounded-lg"
                  title="Redo Layout Change"
                >
                  <Redo2 className="w-4 h-4" />
                </button>
              </div>

              <select
                className="px-2 py-1.5 bg-slate-100 dark:bg-slate-800 text-xs font-bold rounded-lg text-slate-700 dark:text-slate-300 border-none outline-none"
                onChange={(e) => {
                  if (e.target.value) {
                    addWidget(e.target.value as WidgetType);
                    e.target.value = '';
                  }
                }}
                defaultValue=""
              >
                <option value="" disabled>+ Add Widget...</option>
                <option value={WidgetType.CHURN_RISK_TABLE}>Churn Risk Table</option>
                <option value={WidgetType.METRICS_SUMMARY}>Metrics Summary</option>
                <option value={WidgetType.ANALYTICS_ROI}>ROI Analytics</option>
                <option value={WidgetType.ANALYTICS_INTERVENTIONS}>Intervention Performance</option>
                <option value={WidgetType.ANALYTICS_COHORTS}>Cohort Breakdown</option>
                <option value={WidgetType.ANALYTICS_RAR}>Revenue at Risk</option>
              </select>
              <button onClick={resetToDefault} className="px-3 py-1.5 border border-red-500/30 text-red-600 dark:text-red-400 bg-red-500/10 text-xs font-bold rounded-lg hover:bg-red-500/20 transition-colors">Reset</button>
              <button onClick={publishTenantDefault} className="px-3 py-1.5 border border-purple-500/30 text-purple-600 dark:text-purple-400 bg-purple-500/10 text-xs font-bold rounded-lg hover:bg-purple-500/20 transition-colors">Publish Default</button>
              <button onClick={() => setIsEditMode(false)} className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg shadow-md transition-colors">Finish Editing</button>
            </>
          ) : (
            <button onClick={() => setIsEditMode(true)} className="px-4 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg text-xs font-bold text-slate-700 dark:text-slate-300 transition-colors">
              Edit Layout
            </button>
          )}
        </div>
      </div>

      {/* Empty State */}
      {dashboardData.widgets.length === 0 && !isEditMode && (
        <div className="flex flex-col items-center justify-center p-12 bg-white/50 dark:bg-slate-900/50 border border-dashed border-slate-300 dark:border-slate-700 rounded-2xl">
          <p className="text-slate-500 dark:text-slate-400 font-medium mb-4">Your dashboard is empty.</p>
          <button onClick={() => setIsEditMode(true)} className="px-4 py-2 bg-blue-600 text-white text-sm font-bold rounded-xl shadow-md">Start Building</button>
        </div>
      )}

      {/* Grid Canvas */}
      <div className="-mx-2" ref={containerRef as React.RefObject<HTMLDivElement>}>
        {mounted && (
          <ResponsiveGridLayout
            className="layout"
            layouts={dashboardData.layouts}
            breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
            cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
            rowHeight={120}
            onLayoutChange={onLayoutChange}
            width={width}
            dragConfig={{ enabled: isEditMode, handle: '.drag-handle' }}
            resizeConfig={{ enabled: isEditMode }}
            margin={[16, 16]}
          >
          {dashboardData.widgets.map(w => (
            <div key={w.id}>
              <WidgetWrapper 
                widget={w} 
                isEditing={isEditMode} 
                onRemove={removeWidget} 
                onUpdateConfig={updateWidgetConfig}
              >
                {renderWidget(w)}
              </WidgetWrapper>
            </div>
          ))}
          </ResponsiveGridLayout>
        )}
      </div>

      {/* SHAP & Gemini Risk Explanation Modal */}
      {selectedCustomer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl relative transition-colors">
            <button onClick={() => setSelectedCustomer(null)} className="absolute top-4 right-4 p-1 text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
              <X className="w-5 h-5" />
            </button>
            <div>
              <div className="flex items-center space-x-2 text-xs font-extrabold text-blue-600 dark:text-blue-400 uppercase tracking-wider mb-1">
                <Sparkles className="w-4 h-4 text-blue-500" />
                <span>Gemini & SHAP Risk Analysis</span>
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-white font-mono">{selectedCustomer.id}</h3>
              <div className="flex items-center space-x-3 mt-2 text-xs">
                <span className={`px-2.5 py-0.5 rounded-full font-extrabold uppercase border ${selectedCustomer.churn_risk_tier === 'critical' ? 'bg-red-500/10 text-red-700' : 'bg-slate-100 text-slate-700'}`}>
                  {selectedCustomer.churn_risk_tier} Risk Tier
                </span>
                <span className="text-slate-800 dark:text-slate-200 font-bold">
                  Probability: {((selectedCustomer.churn_probability || 0) * 100).toFixed(1)}%
                </span>
                <span className="text-slate-500 dark:text-slate-400 font-medium">MRR: ${selectedCustomer.mrr.toFixed(2)}</span>
              </div>
            </div>

            {outreachSuccess && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 p-3 rounded-xl text-xs flex items-center space-x-2 font-bold">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                <span>{outreachSuccess}</span>
              </div>
            )}

            {/* Gemini Intervention Strategy */}
            <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl space-y-2">
              <div className="flex items-center space-x-2 text-xs font-extrabold text-blue-700 dark:text-blue-300">
                <Sparkles className="w-4 h-4 text-blue-500" />
                <span>Gemini Recommended Strategy</span>
              </div>
              <div className="text-xs font-bold text-slate-900 dark:text-white">{explanation?.intervention_recommendation?.strategy || "Proactive Check-In"}</div>
              <p className="text-xs text-slate-800 dark:text-slate-300 italic bg-white dark:bg-slate-950/60 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800/80">
                &quot;{explanation?.intervention_recommendation?.copy || "Recommend scheduling a 15-minute sync with their admin."}&quot;
              </p>
            </div>

            {/* 1-Click Automated Outreach */}
            <div className="pt-2">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Execute Immediate Retention Campaign</div>
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => { setOutreachSuccess("Outreach sent!"); setTimeout(()=>setOutreachSuccess(null), 3000); }}
                  className="py-2.5 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center space-x-2 shadow-md shadow-blue-500/20"
                >
                  <Mail className="w-4 h-4" />
                  <span>Send Email Offer</span>
                </button>
                <button
                  onClick={() => { setOutreachSuccess("Slack alert sent!"); setTimeout(()=>setOutreachSuccess(null), 3000); }}
                  className="py-2.5 px-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center space-x-2 shadow-md shadow-purple-500/20"
                >
                  <Send className="w-4 h-4" />
                  <span>Slack Alert</span>
                </button>
                <button
                  onClick={() => { setOutreachSuccess("Banner activated!"); setTimeout(()=>setOutreachSuccess(null), 3000); }}
                  className="py-2.5 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center space-x-2 shadow-md shadow-emerald-500/20"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>In-App Banner</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
