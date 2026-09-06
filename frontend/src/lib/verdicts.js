export const VERDICT_STYLES = {
  VERIFIED_SUCCESS: {
    label: "Verified success",
    subtitle: "Every required condition confirmed by explicit evidence.",
    icon: "ShieldCheck",
    badgeClass: "bg-emerald-100 text-emerald-800 border-emerald-300",
    heroClass: "bg-emerald-50 border-emerald-200",
    dot: "bg-emerald-500",
  },
  PARTIAL: {
    label: "Partial",
    subtitle: "Some conditions confirmed. Others remain unverified.",
    icon: "AlertTriangle",
    badgeClass: "bg-amber-100 text-amber-800 border-amber-300",
    heroClass: "bg-amber-50 border-amber-200",
    dot: "bg-amber-500",
  },
  UNKNOWN: {
    label: "Unknown",
    subtitle: "Not enough explicit evidence to decide.",
    icon: "HelpCircle",
    badgeClass: "bg-slate-100 text-slate-700 border-slate-300",
    heroClass: "bg-slate-50 border-slate-200",
    dot: "bg-slate-500",
  },
  FAILED: {
    label: "Failed",
    subtitle: "A required condition failed or was contradicted.",
    icon: "XCircle",
    badgeClass: "bg-rose-100 text-rose-800 border-rose-300",
    heroClass: "bg-rose-50 border-rose-200",
    dot: "bg-rose-500",
  },
  IN_PROGRESS: {
    label: "In progress",
    subtitle: "Call still running.",
    icon: "Loader2",
    badgeClass: "bg-sky-100 text-sky-800 border-sky-300",
    heroClass: "bg-sky-50 border-sky-200",
    dot: "bg-sky-500",
  },
};

export const MODE_BADGE = {
  REAL: "bg-sky-50 text-sky-800 border-sky-200",
  SIMULATED: "bg-violet-50 text-violet-800 border-violet-200",
  NOT_CONFIGURED: "bg-orange-50 text-orange-800 border-orange-200",
  UNKNOWN: "bg-slate-50 text-slate-700 border-slate-200",
};
