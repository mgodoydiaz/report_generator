import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";

export default function Layout({ children }) {
  return (
    <div className="app-shell">
      <Topbar />
      <div className="d-lg-flex">
        <Sidebar />
        <main className="container py-5 layout-main">{children}</main>
      </div>
    </div>
  );
}
