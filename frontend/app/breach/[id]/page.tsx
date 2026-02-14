import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BreachDetail } from "@/components/breach/breach-detail";
import { getBreachById, getRelatedBreaches } from "@/lib/queries/breaches";
import { truncate } from "@/lib/utils/formatting";

export const dynamic = "force-dynamic";

interface BreachPageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({
  params,
}: BreachPageProps): Promise<Metadata> {
  const { id } = await params;
  const breach = await getBreachById(id);
  if (!breach) return { title: "Breach Not Found" };

  return {
    title: `${breach.company} Data Breach`,
    description: breach.summary
      ? truncate(breach.summary, 160)
      : `Details about the ${breach.company} data breach incident.`,
  };
}

export default async function BreachPage({ params }: BreachPageProps) {
  const { id } = await params;
  const [breach, relatedBreaches] = await Promise.all([
    getBreachById(id),
    getRelatedBreaches(id, 3),
  ]);

  if (!breach) notFound();

  return <BreachDetail breach={breach} relatedBreaches={relatedBreaches} />;
}
