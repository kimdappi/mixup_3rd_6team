import { Navigate, Route, Routes } from 'react-router-dom';
import Landing from './pages/Landing.jsx';
import AnalyzeInput from './pages/AnalyzeInput.jsx';
import AnalyzeRunning from './pages/AnalyzeRunning.jsx';
import Result from './pages/Result.jsx';
import Saju from './pages/Saju.jsx';

function SajuGuard({ children }) {
  const unlocked = sessionStorage.getItem('sajuUnlocked') === 'true';
  if (!unlocked) return <Navigate to="/result" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/analyze" element={<AnalyzeInput />} />
      <Route path="/analyze/running" element={<AnalyzeRunning />} />
      <Route path="/result" element={<Result />} />
      <Route
        path="/result/saju"
        element={
          <SajuGuard>
            <Saju />
          </SajuGuard>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
