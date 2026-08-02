import { fetchAPI } from '@/lib/api';
import Link from 'next/link';
import { ArrowLeft, Clock, MessageSquare, AlertTriangle } from 'lucide-react';

export default async function CustomerDetailPage({ params }: { params: { id: string } }) {
  let explanation = null;
  let interventions = [];
  
  try {
    explanation = await fetchAPI(`/customers/${params.id}/churn-explanation`);
  } catch (e) {
    console.error('Failed to fetch explanation:', e);
  }

  try {
    interventions = await fetchAPI(`/customers/${params.id}/interventions`);
  } catch (e) {
    console.error('Failed to fetch interventions:', e);
  }

  return (
    <div>
      <div className="mb-6">
        <Link href="/dashboard" className="text-blue-600 hover:text-blue-800 flex items-center space-x-2">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </Link>
      </div>

      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Customer: {params.id}</h1>
        {explanation ? (
          <div className="flex items-center space-x-4">
            <div className={`px-3 py-1 rounded-full border font-semibold ${
              explanation.risk_tier === 'critical' ? 'bg-red-100 text-red-800 border-red-200' :
              explanation.risk_tier === 'high' ? 'bg-orange-100 text-orange-800 border-orange-200' :
              explanation.risk_tier === 'medium' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
              'bg-green-100 text-green-800 border-green-200'
            }`}>
              {explanation.risk_tier?.toUpperCase()} RISK
            </div>
            <div className="text-gray-500">
              Probability: {(explanation.probability * 100).toFixed(1)}%
            </div>
          </div>
        ) : (
          <div className="text-gray-500">Explanation data unavailable.</div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
            <AlertTriangle className="w-5 h-5 mr-2 text-yellow-500" />
            Top Churn Drivers
          </h2>
          {explanation && explanation.top_drivers && explanation.top_drivers.length > 0 ? (
            <ul className="space-y-3">
              {explanation.top_drivers.map((driver: any, idx: number) => (
                <li key={idx} className="flex justify-between items-start bg-gray-50 p-3 rounded">
                  <span className="text-gray-800 font-medium">{driver.human_readable}</span>
                  <span className="text-sm text-gray-500 font-mono">Impact: {driver.shap_value.toFixed(3)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500">No significant drivers identified.</p>
          )}

          <div className="mt-8">
            <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
              <MessageSquare className="w-5 h-5 mr-2 text-blue-500" />
              AI Recommendation
            </h3>
            {explanation && explanation.recommended_intervention ? (
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 text-blue-900">
                {explanation.recommended_intervention}
              </div>
            ) : (
              <p className="text-gray-500">No recommendation available.</p>
            )}
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
            <Clock className="w-5 h-5 mr-2 text-gray-500" />
            Intervention History
          </h2>
          {interventions.length > 0 ? (
            <div className="flow-root">
              <ul className="-mb-8">
                {interventions.map((intervention: any, idx: number) => (
                  <li key={intervention.id}>
                    <div className="relative pb-8">
                      {idx !== interventions.length - 1 ? (
                        <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true"></span>
                      ) : null}
                      <div className="relative flex space-x-3">
                        <div>
                          <span className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${
                            intervention.status === 'sent' ? 'bg-green-500' :
                            intervention.status === 'failed' ? 'bg-red-500' :
                            'bg-gray-400'
                          }`}>
                            <MessageSquare className="h-4 w-4 text-white" />
                          </span>
                        </div>
                        <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                          <div>
                            <p className="text-sm text-gray-500">
                              <span className="font-medium text-gray-900 uppercase">{intervention.channel}</span> intervention 
                              {intervention.manual_override ? ' (Manual)' : ' (Automated)'}
                            </p>
                            <p className="text-xs text-gray-400 mt-1 uppercase tracking-wider">{intervention.status}</p>
                          </div>
                          <div className="text-right text-sm whitespace-nowrap text-gray-500">
                            {intervention.sent_at ? new Date(intervention.sent_at).toLocaleDateString() : 'Pending'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-gray-500">No past interventions.</p>
          )}
        </div>
      </div>
    </div>
  );
}
