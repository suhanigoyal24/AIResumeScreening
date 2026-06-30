import type { MatchReport } from "../types";

interface MatchReportProps {
  report: MatchReport;
  score: number;
}

export default function MatchReport({ report, score }: MatchReportProps) {
  const getScoreColor = (s: number) => {
    if (s >= 80) return "text-green-600 bg-green-100";
    if (s >= 60) return "text-yellow-600 bg-yellow-100";
    return "text-red-600 bg-red-100";
  };

  const getScoreLabel = (s: number) => {
    if (s >= 80) return "Strong Match";
    if (s >= 60) return "Good Match";
    if (s >= 40) return "Fair Match";
    return "Needs Improvement";
  };

  return (
    <div className="mt-6 p-5 bg-white border border-gray-200 rounded-xl shadow-sm">
      {/* Score Header */}
      <div className="flex items-center gap-4 mb-6">
        <div className={`px-4 py-2 rounded-lg font-bold text-xl ${getScoreColor(score)}`}>
          {score}%
        </div>
        <div>
          <h3 className="font-bold text-lg text-gray-800">{getScoreLabel(score)}</h3>
          <p className="text-sm text-gray-500">Based on keyword & skill alignment</p>
        </div>
      </div>

      {/* Keywords Grid */}
      <div className="grid md:grid-cols-2 gap-4 mb-6">
        <div>
          <h4 className="font-semibold text-green-700 mb-2 flex items-center gap-1">
            ✅ Matched ({report.matched_keywords.length})
          </h4>
          <div className="flex flex-wrap gap-2">
            {report.matched_keywords.map((kw, i) => (
              <span key={i} className="bg-green-50 text-green-700 px-2.5 py-1 rounded-md text-xs font-medium border border-green-200">
                {kw}
              </span>
            ))}
            {report.matched_keywords.length === 0 && <p className="text-gray-400 text-sm">None found</p>}
          </div>
        </div>

        <div>
          <h4 className="font-semibold text-red-700 mb-2 flex items-center gap-1">
            ❌ Missing ({report.missing_keywords.length})
          </h4>
          <div className="flex flex-wrap gap-2">
            {report.missing_keywords.map((kw, i) => (
              <span key={i} className="bg-red-50 text-red-700 px-2.5 py-1 rounded-md text-xs font-medium border border-red-200">
                {kw}
              </span>
            ))}
            {report.missing_keywords.length === 0 && <p className="text-gray-400 text-sm">Great coverage!</p>}
          </div>
        </div>
      </div>

      {/* Section Scores */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-700 mb-3">Section Breakdown</h4>
        <div className="space-y-3">
          {Object.entries(report.section_scores).map(([section, val]) => (
            <div key={section}>
              <div className="flex justify-between text-sm mb-1">
                <span className="capitalize text-gray-600">{section}</span>
                <span className="font-medium">{val}%</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${val}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <h4 className="font-semibold text-indigo-800 mb-2">💡 AI Recommendations</h4>
        <ul className="space-y-1.5 text-sm text-indigo-700 list-disc pl-4">
          {report.recommendations.map((rec, i) => (
            <li key={i}>{rec}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}