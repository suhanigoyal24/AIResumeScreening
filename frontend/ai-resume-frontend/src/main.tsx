// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Ensure the DOM is ready before rendering
const rootElement = document.getElementById("root");

if (!rootElement) {
  console.error("❌ Root element not found. Check your index.html.");
} else {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}