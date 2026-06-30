// src/components/Header.tsx
import { Link, useLocation } from 'react-router-dom';

export default function Header() {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="fixed top-0 left-0 right-0 bg-white shadow-md border-b border-gray-200 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="text-xl font-bold text-gray-900 hover:text-indigo-600 transition flex items-center gap-2">
              <span className="text-2xl">🤖</span>
              <span>ResumeMatcher</span>
            </Link>
          </div>
          <div className="flex items-center space-x-2">
            <Link 
              to="/" 
              className={`px-3 py-2 text-sm font-medium rounded-lg transition ${
                isActive('/') ? 'bg-indigo-50 text-indigo-600' : 'text-gray-700 hover:text-indigo-600'
              }`}
            >
              Home
            </Link>
            <Link 
              to="/upload" 
              className={`px-3 py-2 text-sm font-medium rounded-lg transition ${
                isActive('/upload') ? 'bg-indigo-50 text-indigo-600' : 'text-gray-700 hover:text-indigo-600'
              }`}
            >
              Upload
            </Link>
            <Link 
              to="/dashboard" 
              className={`px-3 py-2 text-sm font-medium rounded-lg transition ${
                isActive('/dashboard') ? 'bg-indigo-50 text-indigo-600' : 'text-gray-700 hover:text-indigo-600'
              }`}
            >
              Dashboard
            </Link>
            <Link 
  to="/history" 
  className={`px-3 py-2 text-sm font-medium rounded-lg transition ${
    isActive('/history') ? 'bg-indigo-50 text-indigo-600' : 'text-gray-700 hover:text-indigo-600'
  }`}
>
  History
</Link>
          </div>
        </div>
      </div>
    </nav>
  );
}