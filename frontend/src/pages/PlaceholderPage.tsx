import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";

interface PlaceholderPageProps {
  title: string;
  phase: string;
  bullets: string[];
}

export function PlaceholderPage({ title, phase, bullets }: PlaceholderPageProps) {
  return (
    <Card className="max-w-[720px]">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <span className="ml-auto rounded-full bg-accent-soft px-2.5 py-0.5 text-xs text-accent">
          {phase}
        </span>
      </CardHeader>
      <CardBody>
        <p className="text-muted">
          Phase 1 lays the shell. This screen lands in the phase shown above.
        </p>
        <ul className="mt-3 space-y-1.5 text-sm">
          {bullets.map((b) => (
            <li key={b} className="relative pl-4 text-muted">
              <span className="absolute left-0 top-2 text-accent">●</span>
              {b}
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}
