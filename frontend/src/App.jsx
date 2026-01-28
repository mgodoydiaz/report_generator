import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home.jsx";
import Workflows from "./pages/Workflows.jsx";
import Resultados from "./pages/Resultados.jsx";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/workflows" element={<Workflows />} />
        <Route path="/resultados" element={<Resultados />} />
      </Routes>
    </Layout>
  );
}
