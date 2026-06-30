import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './index.css';

// Import pages
import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";

function App() {
  return (
    <Router>
      <div className="app">
        {/* Fixed Navigation - Stays at Top */}
        <nav className="fixed top-0 left-0 right-0 bg-white shadow-md border-b border-gray-200 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <Link to="/" className="text-xl font-bold text-gray-900">
                  ATS Checker
                </Link>
              </div>
              <div className="flex items-center space-x-8">
                <Link to="/" className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium">
                  Home
                </Link>
                <Link to="/upload" className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium">
                  Upload
                </Link>
                <Link to="/dashboard" className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium">
                  Dashboard
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content - Add padding for fixed nav */}
        <main className="pt-16">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;