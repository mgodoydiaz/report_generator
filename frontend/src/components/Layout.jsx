import Sidebar from "./Sidebar";

export default function Layout({ children }) {
  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 bg-neutral-950 text-neutral-100">
        {children}
      </main>
    </div>
  );
}
