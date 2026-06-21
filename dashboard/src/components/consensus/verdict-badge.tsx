import { Badge } from "@/components/ui/badge";
import type { Verdict } from "@/lib/types";
import { cn } from "@/lib/utils";

interface VerdictBadgeProps {
  verdict: Verdict;
  className?: string;
}

const CONFIG: Record<Verdict, { label: string; className: string }> = {
  accepted: {
    label: "Accepted",
    className: "bg-emerald-100 text-emerald-800 border-emerald-200",
  },
  rejected: {
    label: "Rejected",
    className: "bg-red-100 text-red-800 border-red-200",
  },
  needs_review: {
    label: "Needs Review",
    className: "bg-amber-100 text-amber-800 border-amber-200",
  },
};

export function VerdictBadge({ verdict, className }: VerdictBadgeProps) {
  const { label, className: colorClass } = CONFIG[verdict];
  return (
    <Badge
      variant="outline"
      className={cn("font-medium", colorClass, className)}
    >
      {label}
    </Badge>
  );
}
