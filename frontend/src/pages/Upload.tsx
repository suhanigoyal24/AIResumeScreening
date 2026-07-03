// src/pages/Upload.tsx
import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, X, ClipboardList } from "lucide-react";
import type { Candidate } from "../types";

export default function UploadPage() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [jobDescription, setJobDescription] = useState("");
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<{
    success: Candidate[];
    errors: Array<{ filename: string; error: string }>;
  }>({ success: [], errors: [] });
  const [dragActive, setDragActive] = useState(false);
  
  // FIX: Only destructure sessionId (we never update it, so no setter needed)
  const [sessionId] = useState<string>(() => 
    `session_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
  );
  
  const [jdMode, setJdMode] = useState<"text" | "file">("text");

  // Handle resume file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).filter(file => 
        file.type === "application/pdf" || file.name.endsWith(".docx")
      );
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  // Handle JD file selection
  const handleJdFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setJdFile(e.target.files[0]);
      // Auto-read JD file content if it's text
      if (e.target.files[0].type === "text/plain" || e.target.files[0].name.endsWith(".txt")) {
        const reader = new FileReader();
        reader.onload = (event) => {
          if (event.target?.result) {
            setJobDescription(event.target.result as string);
          }
        };
        reader.readAsText(e.target.files[0]);
      }
    }
  };

  // Drag & drop handlers for resumes
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files) {
      const newFiles = Array.from(e.dataTransfer.files).filter(file => 
        file.type === "application/pdf" || file.name.endsWith(".docx")
      );
      setFiles(prev => [...prev, ...newFiles]);
    }
  }, []);

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const removeJdFile = () => {
    setJdFile(null);
    if (jdMode === "file") setJobDescription("");
  };

  // Upload to backend
  const handleUpload = async () => {
    if (files.length === 0) {
      setResults({ success: [], errors: [{ filename: "Upload", error: "Please select at least one resume" }] });
      return;
    }
    if (!jobDescription.trim() && !jdFile) {
      setResults({ success: [], errors: [{ filename: "Upload", error: "Please provide a Job Description (paste text or upload file)" }] });
      return;
    }
    
    setUploading(true);
    setResults({ success: [], errors: [] });

    const formData = new FormData();
    formData.append("session_id", sessionId);
    
    // Add job description (text or file)
    if (jobDescription.trim()) {
      formData.append("job_description", jobDescription);
    }
    if (jdFile) {
      formData.append("jd_file", jdFile);
    }
    
    files.forEach(file => {
      formData.append("resumes", file);
    });

    try {
      const response = await fetch("https://gsuhani17-ats-checker-backend.hf.space/api/upload/", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Upload failed: ${response.status}`);
      }

      const data = await response.json();
      
      const successful = data.results?.filter((r: any) => r.success) || [];
      const errors = data.results?.filter((r: any) => !r.success) || [];

      setResults({
        success: successful.map((r: any) => ({
          id: r.candidate_id,
          name: r.filename,
          score: r.score || 0,
          session_id: sessionId,
          match_report: r.match_report,
          ...r
        })),
        errors: errors.map((r: any) => ({
          filename: r.filename,
          error: r.error || "Unknown error"
        }))
      });

      if (successful.length > 0) {
        setFiles([]);
        setJobDescription("");
        setJdFile(null);
      }

    } catch (err: any) {
      console.error("Upload error:", err);
      setResults(prev => ({
        ...prev,
        errors: [...prev.errors, { filename: "Upload", error: err.message }]
      }));
    } finally {
      setUploading(false);
    }
  };

  const goToDashboard = () => {
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800 flex flex-col items-center justify-center p-4 py-8">
      <div className="w-full max-w-4xl">
        
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-3xl md:text-4xl font-extrabold text-white mb-2">
            📄 Upload Resumes for Analysis
          </h1>
        </div>

        {/* Upload Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-5 md:p-7">
          
          {/* ========== JOB DESCRIPTION SECTION ========== */}
          <div className="mb-6 pb-6 border-b border-gray-200">
            <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <ClipboardList className="text-indigo-600" size={20} />
              Job Description (Required)
            </h3>
            
            {/* JD Input Mode Toggle */}
            <div className="flex gap-2 mb-3">
              <button
                type="button"
                onClick={() => setJdMode("text")}
                className={`px-3 py-1.5 text-sm rounded-lg transition ${
                  jdMode === "text" 
                    ? "bg-indigo-600 text-white" 
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                ✍️ Paste Text
              </button>
              <button
                type="button"
                onClick={() => setJdMode("file")}
                className={`px-3 py-1.5 text-sm rounded-lg transition ${
                  jdMode === "file" 
                    ? "bg-indigo-600 text-white" 
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                📎 Upload File
              </button>
            </div>

            {/* JD Text Area */}
            {jdMode === "text" && (
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the job description here (title, requirements, skills, responsibilities...)..."
                className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition min-h-[120px] text-sm"
                disabled={uploading}
              />
            )}

            {/* JD File Upload */}
            {jdMode === "file" && (
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-4 text-center hover:border-indigo-400 transition cursor-pointer">
                <input
                  type="file"
                  accept=".txt,.pdf,.docx"
                  className="hidden"
                  id="jd-file-input"
                  onChange={handleJdFileChange}
                  disabled={uploading}
                />
                <label htmlFor="jd-file-input" className="cursor-pointer">
                  <Upload className="mx-auto h-8 w-8 text-indigo-500 mb-2" />
                  <p className="text-gray-700 font-medium">
                    {jdFile ? jdFile.name : "Click to upload JD file"}
                  </p>
                  <p className="text-gray-500 text-xs mt-1">Supports: TXT, PDF, DOCX</p>
                </label>
                {jdFile && (
                  <button
                    onClick={removeJdFile}
                    className="mt-2 text-red-500 text-sm hover:underline flex items-center gap-1 mx-auto"
                  >
                    <X size={14} /> Remove
                  </button>
                )}
              </div>
            )}

            {/* JD Validation Hint */}
            {!jobDescription.trim() && !jdFile && (
              <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                <AlertCircle size={12} /> Job Description is required for matching
              </p>
            )}
          </div>

          {/* ========== RESUME UPLOAD SECTION ========== */}
          <div className="mb-6">
            <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <FileText className="text-indigo-600" size={20} />
              Candidate Resumes
            </h3>
            
            <div
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer ${
                dragActive 
                  ? "border-indigo-500 bg-indigo-50" 
                  : "border-gray-300 hover:border-indigo-400 hover:bg-gray-50"
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById("file-input")?.click()}
            >
              <input
                id="file-input"
                type="file"
                multiple
                accept=".pdf,.docx"
                className="hidden"
                onChange={handleFileChange}
                disabled={uploading}
              />
              
              <Upload className="mx-auto h-10 w-10 text-indigo-500 mb-3" />
              <p className="text-gray-700 font-medium mb-1">
                {dragActive ? "Drop files here..." : "Drag & drop resumes here"}
              </p>
              <p className="text-gray-500 text-sm mb-2">or click to browse</p>
              <p className="text-xs text-gray-400">Supports: PDF, DOCX (max 10 files)</p>
            </div>

            {/* Selected Files List */}
            {files.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-medium text-gray-700 mb-2">Selected ({files.length}):</p>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {files.map((file, index) => (
                    <div 
                      key={index} 
                      className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-200"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="text-indigo-500 flex-shrink-0" size={16} />
                        <span className="text-sm text-gray-700 truncate">{file.name}</span>
                        <span className="text-xs text-gray-400 flex-shrink-0">
                          ({(file.size / 1024 / 1024).toFixed(2)} MB)
                        </span>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); removeFile(index); }}
                        className="p-1 hover:bg-red-100 rounded-full text-red-500 transition disabled:opacity-50"
                        disabled={uploading}
                        aria-label={`Remove ${file.name}`}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleUpload}
              disabled={files.length === 0 || uploading || (!jobDescription.trim() && !jdFile)}
              className="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              {uploading ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  Analyzing...
                </>
              ) : (
                <>
                  <Upload size={18} />
                  Upload & Analyze ({files.length})
                </>
              )}
            </button>
            
            <button
              onClick={() => navigate("/dashboard")}
              className="px-5 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition flex items-center justify-center gap-2 text-sm"
            >
              ← Dashboard
            </button>
          </div>

          {/* Results Section */}
          {(results.success.length > 0 || results.errors.length > 0) && (
            <div className="mt-6 pt-5 border-t border-gray-200">
              <h4 className="font-semibold text-gray-800 mb-3 text-sm">Results</h4>
              
              {results.success.length > 0 && (
                <div className="mb-3 p-3 bg-green-50 border border-green-200 rounded-xl">
                  <div className="flex items-start gap-2">
                    <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={16} />
                    <div>
                      <p className="font-medium text-green-800 text-sm">
                        ✅ {results.success.length} resume(s) analyzed!
                      </p>
                      <ul className="mt-1 space-y-0.5 text-xs text-green-700">
                        {results.success.slice(0, 3).map((c, i) => (
                          <li key={i}>• {c.name} — {c.score}% match</li>
                        ))}
                        {results.success.length > 3 && (
                          <li className="text-green-600">+ {results.success.length - 3} more...</li>
                        )}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {results.errors.length > 0 && (
                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-xl">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={16} />
                    <div>
                      <p className="font-medium text-red-800 text-sm">
                        ⚠️ {results.errors.length} error(s)
                      </p>
                      <ul className="mt-1 space-y-0.5 text-xs text-red-700">
                        {results.errors.map((err, i) => (
                          <li key={i}>• {err.filename}: {err.error}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {results.success.length > 0 && (
                <button
                  onClick={goToDashboard}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 transition text-sm"
                >
                  <CheckCircle size={16} />
                  View in Dashboard
                </button>
              )}
            </div>
          )}

        </div>

        {/* Help Text */}
        <div className="mt-4 text-center text-blue-100/80 text-xs max-w-2xl mx-auto">
          <p>
            💡 <strong>Tip:</strong> Paste or upload the job description first, then add candidate resumes. 
            The AI will match skills, experience, and keywords.
          </p>
        </div>

      </div>
    </div>
  );
}