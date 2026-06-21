import { redirect } from "next/navigation";

import { completeBankCallback } from "@/lib/api";
import { requireAuth } from "@/lib/session";
import { SearchParams, firstParam } from "@/app/pageUtils";

export const dynamic = "force-dynamic";

export default async function BankCallbackPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  await requireAuth();

  const params = await searchParams;
  const ref = firstParam(params, "ref", "");
  if (!ref) {
    redirect("/bank?message=bank_callback_missing");
  }

  const result = await completeBankCallback(ref);
  if (result.error || !result.data) {
    redirect("/bank?message=bank_callback_failed");
  }

  redirect(`/bank?connection=${result.data.id}&message=connected`);
}
