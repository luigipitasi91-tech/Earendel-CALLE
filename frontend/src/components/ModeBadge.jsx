import { Badge } from "../components/ui/badge";
import { MODE_BADGE } from "../lib/verdicts";

export function ModeBadge({ mode, testId }) {
  const cls = MODE_BADGE[mode] || MODE_BADGE.UNKNOWN;
  return (
    <Badge
      variant="outline"
      data-testid={testId || `mode-badge-${mode}`}
      className={`${cls} font-mono uppercase tracking-wider text-[10px] px-2 py-1`}
    >
      {mode.replace("_", " ")}
    </Badge>
  );
}
