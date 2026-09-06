import { Check } from "lucide-react";

const STEPS = [
  { key: "request", label: "Request" },
  { key: "contract", label: "Contract" },
  { key: "guardian", label: "Guardian" },
  { key: "call", label: "Call" },
  { key: "result", label: "Result" },
];

export function Stepper({ current }) {
  const currentIdx = STEPS.findIndex((s) => s.key === current);
  return (
    <ol
      className="flex items-center justify-between gap-1 w-full text-[11px] font-mono uppercase tracking-wider text-slate-500"
      data-testid="stepper"
    >
      {STEPS.map((s, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        return (
          <li key={s.key} className="flex-1 flex items-center gap-2 min-w-0">
            <span
              className={`shrink-0 grid place-items-center h-6 w-6 rounded-full border ${
                done
                  ? "bg-slate-900 text-white border-slate-900"
                  : active
                    ? "bg-white text-slate-900 border-slate-900"
                    : "bg-white text-slate-400 border-slate-200"
              }`}
              data-testid={`step-${s.key}`}
            >
              {done ? <Check className="h-3 w-3" /> : i + 1}
            </span>
            <span className={`truncate ${active ? "text-slate-900" : ""}`}>{s.label}</span>
            {i < STEPS.length - 1 && <span className="hidden sm:block flex-1 h-px bg-slate-200" />}
          </li>
        );
      })}
    </ol>
  );
}
