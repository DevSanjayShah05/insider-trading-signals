import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Leaderboard from "./pages/Leaderboard";
import EventDetail from "./pages/EventDetail";
import TickerDetail from "./pages/TickerDetail";
import Methodology from "./pages/Methodology";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Leaderboard />} />
        <Route path="/events/:id" element={<EventDetail />} />
        <Route path="/tickers/:ticker" element={<TickerDetail />} />
        <Route path="/methodology" element={<Methodology />} />
      </Routes>
    </Layout>
  );
}
