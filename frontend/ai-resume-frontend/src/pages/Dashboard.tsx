// src/pages/Dashboard.tsx
import { useState, useEffect, useMemo } from "react";
import CandidateCard from "../components/CandidateCard";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Download, LayoutGrid, List, Clock, X } from "lucide-react";
import type { Candidate } from "../types";

export default function Dashboard() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  // SESSION MANAGEMENT
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  // Fetch candidates from Django API
  useEffect(() => {
    const fetchCandidates = async () => {
      try {
        setError(null);
        // Use /api/dashboard/ instead of /api/candidates/
        const response = await fetch(
          "https://gsuhani17-ats-checker-backend.hf.space/api/dashboard/"
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        // Extract candidates array from dashboard response
        const candidateList: Candidate[] = data.candidates ?? [];

        console.log("📥 Fetched candidates:", candidateList);

        // Set current session to most recent (or first available)
        if (candidateList.length > 0 && !currentSessionId) {
          const latestSession =
            candidateList.find((c) => c.session_id)?.session_id ?? "default";
          setCurrentSessionId(latestSession);
        }

        setCandidates(candidateList);
      } catch (err) {
        console.error("❌ Error fetching candidates:", err);
        setError("Failed to load candidates. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    fetchCandidates();
  }, []); // Empty dependency array — avoids infinite re-fetch loop

  // FILTER: Current Session Only
  // Include candidates with null/undefined session_id in current view
  const currentBatch = useMemo(() => {
    if (!currentSessionId) return candidates;
    return candidates.filter(
      (c) => !c.session_id || c.session_id === currentSessionId
    );
  }, [candidates, currentSessionId]);

  // GROUP: Previous Sessions for History View
  const previousSessions = useMemo(() => {
    if (!currentSessionId) return [];

    const grouped = candidates
      .filter((c) => c.session_id && c.session_id !== currentSessionId)
      .reduce((acc, c) => {
        const sid = c.session_id!;
        if (!acc[sid]) acc[sid] = [];
        acc[sid].push(c);
        return acc;
      }, {} as Record<string, Candidate[]>);

    return Object.entries(grouped).map(([sessionId, batch]) => ({
      sessionId,
      count: batch.length,
      avgScore: Math.round(
        batch.reduce((sum, c) => sum + c.score, 0) / batch.length
      ),
      topCandidate: batch.reduce(
        (top, c) => (c.score > top.score ? c : top),
        batch[0]
      ).name,
      date: new Date().toLocaleDateString(),
    }));
  }, [candidates, currentSessionId]);

  // FILTER + SORT for Display
  const filteredCandidates = currentBatch
    .filter((c) => {
      const matchesSearch = c.name
        .toLowerCase()
        .includes(search.toLowerCase());
      const meetsScore = c.score >= minScore;
      return matchesSearch && meetsScore;
    })
    .sort((a, b) => b.score - a.score);

  // CSV Export (current filtered view)
  const exportToCSV = () => {
    const headers = ["Name", "Score", "Session", "Matched Keywords", "Status"];
    const rows = filteredCandidates.map((c) => [
      c.name,
      c.score,
      c.session_id?.slice(0, 8) || "N/A",
      (c.match_report?.matched_keywords || []).join("; "),
      c.score >= 80
        ? "Strong Match"
        : c.score >= 60
        ? "Good Match"
        : "Needs Review",
    ]);

    const csv = [headers, ...rows]
      .map((r) => r.map((cell) => `"${cell}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ats_session_${currentSessionId?.slice(0, 8) || "export"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Switch to a previous session
  const loadSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setShowHistory(false);
    setSearch("");
    setMinScore(0);
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading candidates...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 max-w-md text-center">
          <p className="text-red-600 font-medium mb-2">⚠️ {error}</p>
          <button
            onClick={() => window.location.reload()}
            className="text-red-700 underline text-sm hover:text-red-900"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="min-h-screen bg-gray-50 p-4 md:p-6">
        {/* Header */}
        <header className="text-center mb-6">
          <h1 className="text-3xl md:text-4xl font-extrabold text-gray-800">
            🚀 AI Resume Screening Dashboard
          </h1>
        </header>

        {/* Session Controls */}
        <div className="flex flex-wrap gap-3 mb-6 justify-center">
          <button
            onClick={() => (window.location.href = "/upload")}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition font-medium"
          >
            ➕ Upload New Resumes
          </button>
          <button
            onClick={() => setShowHistory(!showHistory)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition font-medium ${
              showHistory
                ? "bg-gray-800 text-white"
                : "bg-white border border-gray-300 hover:bg-gray-50 text-gray-700"
            }`}
          >
            <Clock size={16} /> {showHistory ? "Hide" : "View"} Previous (
            {previousSessions.length})
          </button>
        </div>

        {/* HISTORY MODAL */}
        {showHistory && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
              <div className="flex items-center justify-between p-4 border-b">
                <h3 className="font-bold text-lg text-gray-800">
                  📚 Previous Sessions
                </h3>
                <button
                  onClick={() => setShowHistory(false)}
                  className="p-2 hover:bg-gray-100 rounded-lg transition"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="p-4 overflow-y-auto max-h-[60vh]">
                {previousSessions.length === 0 ? (
                  <p className="text-center text-gray-500 py-8">
                    No previous sessions yet
                  </p>
                ) : (
                  <div className="space-y-3">
                    {previousSessions.map((session) => (
                      <div
                        key={session.sessionId}
                        className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border hover:bg-gray-100 transition cursor-pointer"
                        onClick={() => loadSession(session.sessionId)}
                      >
                        <div>
                          <p className="font-medium text-gray-800">
                            Session {session.sessionId.slice(0, 8)}...
                          </p>
                          <p className="text-sm text-gray-500">
                            {session.count} candidates • Avg: {session.avgScore}
                            % • {session.date}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-indigo-600">
                            Top: {session.topCandidate}
                          </p>
                          <span className="text-xs text-blue-600 hover:underline">
                            View Details →
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* CURRENT SESSION VIEW */}
        {!showHistory && (
          <>
            {/* Filters */}
            <div className="bg-white p-4 rounded-xl shadow-sm mb-4 flex flex-col md:flex-row gap-4">
              <input
                type="text"
                placeholder="Search by name..."
                className="border border-gray-300 p-2.5 rounded-lg w-full focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
                value={search}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setSearch(e.target.value)
                }
                aria-label="Search candidates"
              />
              <select
                className="border border-gray-300 p-2.5 rounded-lg w-full md:w-48 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
                value={minScore}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                  setMinScore(Number(e.target.value))
                }
                aria-label="Filter by minimum score"
              >
                <option value={0}>All Scores</option>
                <option value={60}>60%+</option>
                <option value={75}>75%+</option>
                <option value={85}>85%+</option>
              </select>
            </div>

            {/* View Toggle + Export */}
            <div className="flex justify-between items-center mb-2">
              <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${
                    viewMode === "grid"
                      ? "bg-white shadow text-gray-900"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  <LayoutGrid size={16} /> Grid
                </button>
                <button
                  onClick={() => setViewMode("table")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${
                    viewMode === "table"
                      ? "bg-white shadow text-gray-900"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  <List size={16} /> Table
                </button>
              </div>

              <button
                onClick={exportToCSV}
                disabled={filteredCandidates.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition"
              >
                <Download size={16} /> Export CSV
              </button>
            </div>

            {/* Candidate Display */}
            {viewMode === "grid" ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mt-2">
                {filteredCandidates.map((candidate, index) => (
                  <div key={candidate.id || index} className="relative group">
                    {index === 0 && filteredCandidates.length > 0 && (
                      <span className="absolute -top-2 -right-2 bg-gradient-to-r from-yellow-400 to-amber-500 text-white px-3 py-1 text-xs font-bold rounded-full shadow-lg z-10">
                        🏆 #1
                      </span>
                    )}
                    <CandidateCard {...candidate} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-2 bg-white rounded-xl shadow-sm overflow-hidden border border-gray-200">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="p-4 font-semibold text-gray-700">
                          Candidate
                        </th>
                        <th className="p-4 font-semibold text-gray-700">
                          Score
                        </th>
                        <th className="p-4 font-semibold text-gray-700">
                          Matched Keywords
                        </th>
                        <th className="p-4 font-semibold text-gray-700">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredCandidates.map((c, i) => (
                        <tr
                          key={c.id || i}
                          className="border-b hover:bg-gray-50 transition"
                        >
                          <td className="p-4 font-medium text-gray-900">
                            {c.name}
                          </td>
                          <td className="p-4">
                            <span
                              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                                c.score >= 80
                                  ? "bg-green-100 text-green-800"
                                  : c.score >= 60
                                  ? "bg-yellow-100 text-yellow-800"
                                  : "bg-red-100 text-red-800"
                              }`}
                            >
                              {c.score}%
                            </span>
                          </td>
                          <td className="p-4 text-gray-600 max-w-xs truncate">
                            {(c.match_report?.matched_keywords || [])
                              .slice(0, 4)
                              .join(", ")}
                            {(c.match_report?.matched_keywords || []).length >
                              4 && " +"}
                          </td>
                          <td className="p-4">
                            <span
                              className={`text-xs font-medium ${
                                c.score >= 80
                                  ? "text-green-600"
                                  : c.score >= 60
                                  ? "text-yellow-600"
                                  : "text-red-600"
                              }`}
                            >
                              {c.score >= 80
                                ? "Strong Match"
                                : c.score >= 60
                                ? "Good Match"
                                : "Needs Review"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {filteredCandidates.length === 0 && (
                  <p className="text-center py-8 text-gray-500">
                    No candidates match your filters
                  </p>
                )}
              </div>
            )}

            {/* Empty State */}
            {filteredCandidates.length === 0 && viewMode === "grid" && (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">🔍</div>
                <p className="text-gray-500 text-lg font-medium">
                  {currentBatch.length === 0
                    ? "🚫 No candidates yet. Go to Upload to start analyzing!"
                    : "No candidates match your filters. Try adjusting your search."}
                </p>
              </div>
            )}

            {/* COMPARISON CHART */}
            {filteredCandidates.length > 0 && (
              <div className="bg-white p-6 rounded-2xl shadow-sm mt-10 max-w-4xl mx-auto">
                <h2 className="text-xl font-bold mb-4 text-center text-gray-800">
                  📊 Current Session Comparison
                </h2>
                <p className="text-center text-sm text-gray-500 mb-4">
                  Top {Math.min(filteredCandidates.length, 10)} candidates by
                  score
                </p>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={filteredCandidates.slice(0, 10)}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <XAxis
                      dataKey="name"
                      stroke="#6b7280"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      interval={0}
                      angle={-35}
                      textAnchor="end"
                      height={55}
                    />
                    <YAxis
                      stroke="#6b7280"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      domain={[0, 100]}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#fff",
                        border: "1px solid #e5e7eb",
                        borderRadius: "8px",
                        boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                      }}
                      cursor={{ fill: "#f3f4f6" }}
                    />
                    <Bar
                      dataKey="score"
                      fill="#6366F1"
                      radius={[5, 5, 0, 0]}
                      animationDuration={400}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}