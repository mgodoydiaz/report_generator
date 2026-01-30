import { Routes, Route } from "react-router-dom";
import { Toaster } from 'react-hot-toast';
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home.jsx";
import Pipelines from "./pages/Pipelines.jsx";
import Templates from "./pages/Templates.jsx";
import Results from "./pages/Results.jsx";
import Execution from "./pages/Execution.jsx";
import Values from "./pages/Values.jsx";
import Dimensions from "./pages/Dimensions.jsx";
import Metrics from "./pages/Metrics.jsx";
import Help from "./pages/Help.jsx";

export default function App() {
  return (
    <Layout>
      <Toaster position="top-right" reverseOrder={true} />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/pipelines" element={<Pipelines />} />
        <Route path="/templates" element={<Templates />} />
        <Route path="/results" element={<Results />} />
        <Route path="/execution" element={<Execution />} />
        <Route path="/values" element={<Values />} />
        <Route path="/dimensions" element={<Dimensions />} />
        <Route path="/metrics" element={<Metrics />} />
        <Route path="/help" element={<Help />} />
      </Routes>
    </Layout>
  );
}
