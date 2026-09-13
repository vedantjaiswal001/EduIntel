import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { GraduationCap } from "lucide-react";
import { NAV_ITEMS } from "./nav";
import { getHealth } from "@/lib/api";
import { cn } from "@/lib/cn";

function HealthPill() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 30000 });
  const up = data?.database === "up";
  return (
    <div className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2 text-xs text-white/70 ring-1 ring-white/10">
      <span className={cn("relative flex h-2 w-2")}>
        <span className={cn("absolute inline-flex h-full w-full rounded-full opacity-75", up && "animate-ping bg-emerald-400")} />
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", up ? "bg-emerald-400" : "bg-white/30")} />
      </span>
      {data ? (up ? "API + DB healthy" : "DB unavailable") : "Checking…"}
    </div>
  );
}

export default function Layout() {
  const groups = Array.from(new Set(NAV_ITEMS.map((i) => i.group)));
  return (
    <div className="flex h-full">
      <aside className="flex w-64 shrink-0 flex-col bg-night-grad">
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-grad shadow-glow">
            <GraduationCap className="h-5 w-5 text-white" strokeWidth={2.2} />
          </div>
          <div>
            <div className="font-display text-base font-bold leading-tight text-white">EduIntel</div>
            <div className="text-[11px] text-white/50">Education Intelligence</div>
          </div>
        </div>

        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-2">
          {groups.map((group) => (
            <div key={group}>
              <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-white/35">{group}</div>
              <div className="space-y-1">
                {NAV_ITEMS.filter((i) => i.group === group).map((item) => (
                  <NavLink key={item.path} to={item.path} end={item.path === "/"}
                    className={({ isActive }) => cn("nav-link", isActive && "nav-link-active")}>
                    <item.icon className="h-4 w-4" strokeWidth={2} />
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="space-y-2 px-3 pb-4">
          <div className="chip w-full justify-center !bg-white/5 !text-white/50 ring-1 ring-white/10">synthetic demo data</div>
          <HealthPill />
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1440px] px-6 py-7">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
