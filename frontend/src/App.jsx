import { Routes, Route } from "react-router-dom";
import { Toaster } from 'react-hot-toast';
import { ThemeProvider } from './context/ThemeContext.jsx';
import Layout from "./layouts/Layout.jsx";
import Home from "./pages/Home.jsx";
import Pipelines from "./pages/Pipelines.jsx";
import Specs from "./pages/Specs.jsx";
import Results from "./pages/Results.jsx";
import Resultspy from "./pages/Resultspy.jsx";
import ResultsRecharts from "./pages/ResultsRecharts.jsx";
import Execution from "./pages/Execution.jsx";
import Values from "./pages/Values.jsx";
import Dimensions from "./pages/Dimensions.jsx";
import Metrics from "./pages/Metrics.jsx";
import Indicators from "./pages/Indicators.jsx";
import Functions from "./pages/Functions.jsx";
import Help from "./pages/Help.jsx";

export default function App() {
  return (
    <ThemeProvider>
      <Layout>
        <Toaster position="top-right" reverseOrder={true} />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/pipelines" element={<Pipelines />} />
          <Route path="/specs" element={<Specs />} />
          <Route path="/results" element={<Results />} />
          <Route path="/results-py" element={<Resultspy />} />
          <Route path="/results-recharts" element={<ResultsRecharts />} />
          <Route path="/execution" element={<Execution />} />
          <Route path="/values" element={<Values />} />
          <Route path="/dimensions" element={<Dimensions />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/indicators" element={<Indicators />} />
          <Route path="/functions" element={<Functions />} />
          <Route path="/help" element={<Help />} />
        </Routes>
      </Layout>
    </ThemeProvider>
  );
}
