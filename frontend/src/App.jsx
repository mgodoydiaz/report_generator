import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home.jsx";
import Pipelines from "./pages/Pipelines.jsx";
import Plantillas from "./pages/Plantillas.jsx";
import Resultados from "./pages/Resultados.jsx";
import Ejecucion from "./pages/Ejecucion.jsx";
import Valores from "./pages/Valores.jsx";
import Dimensiones from "./pages/Dimensiones.jsx";
import Metricas from "./pages/Metricas.jsx";
import Ayuda from "./pages/Ayuda.jsx";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/pipelines" element={<Pipelines />} />
        <Route path="/plantillas" element={<Plantillas />} />
        <Route path="/resultados" element={<Resultados />} />
        <Route path="/ejecucion" element={<Ejecucion />} />
        <Route path="/valores" element={<Valores />} />
        <Route path="/dimensiones" element={<Dimensiones />} />
        <Route path="/metricas" element={<Metricas />} />
        <Route path="/ayuda" element={<Ayuda />} />
      </Routes>
    </Layout>
  );
}
