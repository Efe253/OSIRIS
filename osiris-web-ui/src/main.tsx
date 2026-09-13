import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Not: yönlendirici App içinde (HashRouter — /ui/ alt-yolunda çalışır).
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
