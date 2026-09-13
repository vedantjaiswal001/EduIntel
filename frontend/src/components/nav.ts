import {
  LayoutDashboard,
  Users,
  BookOpen,
  Network,
  MessageSquare,
  Bot,
  Library,
  HeartPulse,
  Cpu,
  FlaskConical,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  group: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Executive Dashboard", path: "/", icon: LayoutDashboard, group: "Overview" },
  { label: "Student 360", path: "/students", icon: Users, group: "Analytics" },
  { label: "Course Intelligence", path: "/courses", icon: BookOpen, group: "Analytics" },
  { label: "Topic Intelligence", path: "/topics", icon: Network, group: "Analytics" },
  { label: "Feedback Intelligence", path: "/feedback", icon: MessageSquare, group: "Analytics" },
  { label: "AI Education Analyst", path: "/analyst", icon: Bot, group: "Intelligence" },
  { label: "Knowledge Base", path: "/knowledge", icon: Library, group: "Intelligence" },
  { label: "Intervention Center", path: "/interventions", icon: HeartPulse, group: "Action" },
  { label: "ML Model Center", path: "/models", icon: Cpu, group: "ML Ops" },
  { label: "Experiment Tracking", path: "/experiments", icon: FlaskConical, group: "ML Ops" },
];
