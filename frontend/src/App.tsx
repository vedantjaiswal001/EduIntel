import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Students from "./pages/Students";
import StudentDetail from "./pages/StudentDetail";
import Courses from "./pages/Courses";
import CourseDetail from "./pages/CourseDetail";
import Topics from "./pages/Topics";
import TopicDetail from "./pages/TopicDetail";
import Feedback from "./pages/Feedback";
import Analyst from "./pages/Analyst";
import KnowledgeBase from "./pages/KnowledgeBase";
import Interventions from "./pages/Interventions";
import Models from "./pages/Models";
import Experiments from "./pages/Experiments";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/students" element={<Students />} />
        <Route path="/students/:id" element={<StudentDetail />} />
        <Route path="/courses" element={<Courses />} />
        <Route path="/courses/:id" element={<CourseDetail />} />
        <Route path="/topics" element={<Topics />} />
        <Route path="/topics/:id" element={<TopicDetail />} />
        <Route path="/feedback" element={<Feedback />} />
        <Route path="/analyst" element={<Analyst />} />
        <Route path="/knowledge" element={<KnowledgeBase />} />
        <Route path="/interventions" element={<Interventions />} />
        <Route path="/models" element={<Models />} />
        <Route path="/experiments" element={<Experiments />} />
      </Route>
    </Routes>
  );
}
