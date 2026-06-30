// src/components/CandidateCard.tsx
import type { CandidateCardProps } from "../types"; // Must use "import type" for interfaces

export default function CandidateCard({ 
  name, 
  score, 
  skills, 
  resume_url 
}: CandidateCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 85) return "text-green-600 bg-green-100";
    if (score >= 70) return "text-yellow-600 bg-yellow-100";
    return "text-red-600 bg-red-100";
  };

  return (
    <div className="bg-white p-5 rounded-xl shadow-md hover:shadow-xl transition-all duration-200 border border-gray-100">
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-bold text-lg text-gray-800 truncate">{name}</h3>
        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getScoreColor(score)}`}>
          {score}%
        </span>
      </div>

      {skills && skills.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-gray-500 mb-2">Top Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {skills.slice(0, 5).map((skill, index) => (
              <span 
                key={index} 
                className="bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-md text-xs font-medium"
              >
                {skill}
              </span>
            ))}
            {skills.length > 5 && (
              <span className="text-gray-400 text-xs">+{skills.length - 5} more</span>
            )}
          </div>
        </div>
      )}

      {resume_url && (
        <a 
          href={resume_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors"
        >
          View Resume →
        </a>
      )}
    </div>
  );
}