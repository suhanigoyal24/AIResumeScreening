// src/pages/History.tsx
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

// Updated interface: single 'score' only + file_url for viewing resumes
interface HistoryCandidate {
  id: number;
  name: string;
  score: number;              // SINGLE SCORE (not ml_score + traditional_score)
  verdict: string;
  batch_id: string;
  analyzed_at: string;
  skills_count: number;
  file_url?: string;          // ADDED: URL to view/download resume
}

interface Pagination {
  page: number;
  total_pages: number;
  total: number;
}

export default function History() {
  const [candidates, setCandidates] = useState<HistoryCandidate[]>([]);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [minScore, setMinScore] = useState(0);

  const fetchHistory = async (page = 1) => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        page: page.toString(),
        search,
        min_score: minScore.toString()
      });
      
      const res = await fetch(`http://127.0.0.1:8000/api/dashboard/history/?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const data = await res.json();
      setCandidates(data.results || []);
      setPagination(data.pagination || null);
    } catch (err: any) {
      console.error("❌ Fetch error:", err);
      setError(err.message || "Failed to load history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchHistory(); }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchHistory(1);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">📚 Analysis History</h1>
            <p className="text-gray-600 mt-1">View all previously analyzed resumes</p>
          </div>
          <Link to="/dashboard" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            ← Back to Latest
          </Link>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <p className="font-medium">❌ Error: {error}</p>
          </div>
        )}

        {/* Filters */}
        <form onSubmit={handleSearch} className="mb-6 p-4 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <input
              type="text"
              placeholder="Name or skill..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div className="w-40">
            <label className="block text-sm font-medium text-gray-700 mb-1">Min Score</label>
            <select
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value={0}>All</option>
              <option value={40}>40%+</option>
              <option value={60}>60%+</option>
              <option value={80}>80%+</option>
            </select>
          </div>
          <button type="submit" className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            Filter
          </button>
        </form>

        {/* Results Table - Updated for single score */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left p-4 font-medium text-gray-600">Candidate</th>
                <th className="text-left p-4 font-medium text-gray-600">Score</th>
                <th className="text-left p-4 font-medium text-gray-600">Verdict</th>
                <th className="text-left p-4 font-medium text-gray-600">Date</th>
                <th className="text-left p-4 font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {candidates.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50 transition">
                  <td className="p-4">
                    <div className="font-medium text-gray-900">{c.name}</div>
                    <div className="text-xs text-gray-500">{c.skills_count} skills</div>
                  </td>
                  
                  {/* Single Score Badge */}
                  <td className="p-4">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${
                      c.score >= 70 ? 'bg-green-100 text-green-800' :
                      c.score >= 40 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {c.score}%
                    </span>
                  </td>
                  
                  <td className="p-4">
                    <span className={`text-sm font-medium ${
                      c.verdict === 'Shortlist' ? 'text-green-600' : 'text-gray-500'
                    }`}>
                      {c.verdict}
                    </span>
                  </td>
                  
                  <td className="p-4 text-gray-500 text-sm">
                    {new Date(c.analyzed_at).toLocaleDateString()}
                  </td>
                  
                  {/* FIXED: View Details button now opens resume */}
                  <td className="p-4">
                    {c.file_url ? (
                      <a
                        href={c.file_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        View Details
                      </a>
                    ) : (
                      <span className="text-gray-400 text-sm">No file</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {/* Empty State */}
          {candidates.length === 0 && !error && (
            <div className="p-8 text-center text-gray-500">
              <p className="text-4xl mb-2">📭</p>
              <p className="font-medium">No analyses found</p>
              <p className="text-sm mt-1">
                {search || minScore > 0 
                  ? "Try clearing filters." 
                  : "Upload resumes first via /upload"}
              </p>
            </div>
          )}
        </div>

        {/* Pagination */}
        {pagination && pagination.total_pages > 1 && (
          <div className="mt-6 flex justify-center gap-2">
            {Array.from({ length: pagination.total_pages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => fetchHistory(page)}
                className={`px-4 py-2 rounded-lg font-medium transition ${
                  page === pagination.page ? 'bg-blue-600 text-white' : 'bg-white border border-gray-300'
                }`}
              >
                {page}
              </button>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}