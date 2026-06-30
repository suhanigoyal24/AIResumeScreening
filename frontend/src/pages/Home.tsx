import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="min-h-screen bg-blue-600 flex flex-col items-center justify-center text-white px-4 py-12">
      {/* Title */}
      <h1 className="text-5xl font-extrabold mb-4 text-center">
        🤖 AI Resume Screening System
      </h1>

      {/* Subtitle */}
      <p className="text-lg text-center max-w-xl mb-8">
        Upload resumes, analyze skills, rank candidates, and visualize
        performance all powered by AI.
      </p>

      {/* Buttons */}
      <div className="flex gap-4 mb-12">
        <Link to="/upload">
          <button className="bg-white text-blue-600 px-6 py-3 rounded-xl font-semibold shadow-lg hover:scale-105 transition">
            📄 Upload Resume
          </button>
        </Link>

        <Link to="/dashboard">
          <button className="bg-black px-6 py-3 rounded-xl font-semibold shadow-lg hover:scale-105 transition">
            📊 View Dashboard
          </button>
        </Link>
      </div>

      {/* Features Section */}
      <div className="grid md:grid-cols-3 gap-6 text-center w-full max-w-5xl">
        <div className="bg-white text-black p-6 rounded-xl shadow-lg">
          <h3 className="text-xl font-bold mb-2">📄 Resume Parsing</h3>
          <p>Upload PDF resumes and extract skills automatically.</p>
        </div>

        <div className="bg-white text-black p-6 rounded-xl shadow-lg">
          <h3 className="text-xl font-bold mb-2">📊 Smart Scoring</h3>
          <p>Rank candidates based on ATS-style scoring system.</p>
        </div>

        <div className="bg-white text-black p-6 rounded-xl shadow-lg">
          <h3 className="text-xl font-bold mb-2">📈 Data Visualization</h3>
          <p>Interactive charts to compare candidate performance.</p>
        </div>
      </div>
    </div>
  );
}