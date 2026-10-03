"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { FindingBody } from "@/components/FindingDrawer";

export default function FindingPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <div className="mx-auto max-w-3xl">
      <Link href="/workbench" className="mb-3 inline-flex items-center gap-1 font-semibold text-orange-deep">
        <ArrowLeft className="size-4" aria-hidden /> All Findings
      </Link>
      <div className="card p-5">
        <FindingBody findingId={id} />
      </div>
    </div>
  );
}
