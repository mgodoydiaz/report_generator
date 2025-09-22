import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Inicio from "./pages/Inicio";
import Plantillas from "./pages/Plantillas";
import GenerarInforme from "./pages/GenerarInforme";

function App() {
    return (
        <BrowserRouter>
            <Layout>
                <Routes>
                    <Route path="/" element={<Inicio />} />   {/* Página inicial */}
                    <Route path="/inicio" element={<Inicio />} />
                    <Route path="/plantillas" element={<Plantillas />} />
                    <Route path="/generar-informe" element={<GenerarInforme />} />
                </Routes>
            </Layout>
        </BrowserRouter>
    );
}

export default App;