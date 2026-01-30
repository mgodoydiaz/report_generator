import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home.jsx";
import Workflows from "./pages/Workflows.jsx";
import Templates from "./pages/Templates.jsx";
import Resultados from "./pages/Resultados.jsx";
import Execution from "./pages/Execution.jsx";
import Valores from "./pages/Valores.jsx";
import Dimensiones from "./pages/Dimensiones.jsx";
import Metricas from "./pages/Metricas.jsx";
import Ayuda from "./pages/Ayuda.jsx";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/workflows" element={<Workflows />} />
        <Route path="/templates" element={<Templates />} />
        <Route path="/resultados" element={<Resultados />} />
        <Route path="/execution" element={<Execution />} />
        <Route path="/valores" element={<Valores />} />
        <Route path="/dimensiones" element={<Dimensiones />} />
        <Route path="/metricas" element={<Metricas />} />
        <Route path="/ayuda" element={<Ayuda />} />
      </Routes>
    </Layout>
  );
}
