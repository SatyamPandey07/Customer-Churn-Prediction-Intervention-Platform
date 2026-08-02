"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { DollarSign, Percent, TrendingUp } from 'lucide-react';

export default function ClientAnalytics({ performance, roi }: { performance: any[], roi: any }) {
  
  // Format data for recharts
  const chartData = performance.map(p => ({
    name: `${p.intervention_type} (${p.channel})`,
    SuccessRate: parseFloat((p.success_rate * 100).toFixed(1)),
    LowerBound: parseFloat((p.confidence_interval_lower * 100).toFixed(1)),
    UpperBound: parseFloat((p.confidence_interval_upper * 100).toFixed(1)),
    Sample: p.total_interventions
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 shadow rounded-lg flex items-center space-x-4">
          <div className="p-3 rounded-full bg-green-100 text-green-600">
            <DollarSign className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-gray-500 font-medium">Revenue Saved</p>
            <p className="text-2xl font-bold text-gray-900">${roi?.revenue_saved?.toLocaleString() || '0'}</p>
          </div>
        </div>
        
        <div className="bg-white p-6 shadow rounded-lg flex items-center space-x-4">
          <div className="p-3 rounded-full bg-blue-100 text-blue-600">
            <TrendingUp className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-gray-500 font-medium">ROI Multiple</p>
            <p className="text-2xl font-bold text-gray-900">{roi?.roi_multiple ? roi.roi_multiple.toFixed(1) + 'x' : '0x'}</p>
          </div>
        </div>

        <div className="bg-white p-6 shadow rounded-lg flex flex-col justify-center">
          <p className="text-xs text-gray-500 italic mb-2">* Methodology: ROI assumes a 50% counterfactual success rate (i.e., half the retained customers would have stayed anyway). Costs are estimated based on tier MRR and standard retention CAC averages.</p>
          <p className="text-xs text-gray-500 italic">Report Date: {roi?.report_date ? new Date(roi.report_date).toLocaleDateString() : 'N/A'}</p>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-6">Intervention Success Rate (Wilson Score Interval)</h2>
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis tickFormatter={(val) => `${val}%`} />
              <Tooltip formatter={(val, name) => [val + '%', name]} />
              <Legend />
              <Bar dataKey="SuccessRate" fill="#3b82f6" name="Success Rate %" />
              <Bar dataKey="LowerBound" fill="#93c5fd" name="Lower Bound % (95% CI)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
