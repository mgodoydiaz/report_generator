import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from 'react-hot-toast';
import { ThemeProvider } from './context/ThemeContext.jsx';
import { AuthProvider, useAuth } from './context/AuthContext.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import Layout from "./layouts/Layout.jsx";
import Login from "./pages/Login.jsx";
import Home from "./pages/Home.jsx";
import Pipelines from "./pages/Pipelines.jsx";
import Specs from "./pages/Specs.jsx";
import Tables from "./pages/Tables.jsx";
import Results from "./pages/Results.jsx";
import ResultsRecharts from "./pages/ResultsRecharts.jsx";
import Execution from "./pages/Execution.jsx";
import Values from "./pages/Values.jsx";
import Dimensions from "./pages/Dimensions.jsx";
import Metrics from "./pages/Metrics.jsx";
import Indicators from "./pages/Indicators.jsx";
import Functions from "./pages/Functions.jsx";
import Help from "./pages/Help.jsx";
import Users from "./pages/Users.jsx";
import SuperAdmin from "./pages/SuperAdmin.jsx";

function SuperAdminGuard({ children }) {
  const { user } = useAuth();
  if (!user?.is_superadmin) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Toaster position="top-right" reverseOrder={true} />
        <Routes>
          {/* Ruta pública */}
          <Route path="/login" element={<Login />} />

          {/* Rutas protegidas */}
          <Route path="/*" element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/pipelines" element={<Pipelines />} />
                  <Route path="/specs" element={<Specs />} />
                  <Route path="/tables" element={<Tables />} />
                  <Route path="/results" element={<Results />} />
                  <Route path="/results-recharts" element={<ResultsRecharts />} />
                  <Route path="/execution" element={<Execution />} />
                  <Route path="/values" element={<Values />} />
                  <Route path="/dimensions" element={<Dimensions />} />
                  <Route path="/metrics" element={<Metrics />} />
                  <Route path="/indicators" element={<Indicators />} />
                  <Route path="/functions" element={<Functions />} />
                  <Route path="/users" element={<Users />} />
                  <Route path="/superadmin" element={<SuperAdminGuard><SuperAdmin /></SuperAdminGuard>} />
                  <Route path="/help" element={<Help />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          } />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  );
}
