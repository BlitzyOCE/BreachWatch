import Link from "next/link";
import { Shield } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t bg-background">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-medium">BreachWatch</span>
          </div>
          <p className="text-center text-sm text-muted-foreground">
            Breach data is aggregated from public sources and analyzed using AI.
            Information may not be fully accurate.
          </p>
          <nav className="flex gap-4">
            <Link
              href="/about"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              About
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
