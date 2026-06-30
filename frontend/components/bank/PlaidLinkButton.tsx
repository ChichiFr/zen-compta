"use client";

import { useCallback, useState } from "react";
import { usePlaidLink } from "react-plaid-link";

import { completePlaidConnectionAction } from "@/app/actions";

interface Props {
  linkToken: string;
  reference: string;
}

export function PlaidLinkButton({ linkToken, reference }: Props) {
  const [loading, setLoading] = useState(false);

  const onSuccess = useCallback(
    async (publicToken: string) => {
      setLoading(true);
      const connectionId = await completePlaidConnectionAction(
        reference,
        publicToken,
      );
      window.location.href = connectionId
        ? `/bank?connection=${connectionId}&message=connected`
        : "/bank?message=bank_callback_failed";
    },
    [reference],
  );

  const { open, ready } = usePlaidLink({ token: linkToken, onSuccess });

  return (
    <button
      className="rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
      disabled={!ready || loading}
      onClick={() => open()}
      type="button"
    >
      {loading ? "Connexion..." : "Connecter une banque"}
    </button>
  );
}
