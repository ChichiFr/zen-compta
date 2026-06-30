"use client";

import { useState } from "react";

import { getPlaidLinkTokenAction } from "@/app/actions";

import { PlaidLinkButton } from "./PlaidLinkButton";

export function PlaidConnectSection() {
  const [tokenData, setTokenData] = useState<{
    link_token: string;
    reference: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  async function loadToken() {
    setLoading(true);
    setFailed(false);
    const nextTokenData = await getPlaidLinkTokenAction();
    setTokenData(nextTokenData);
    setFailed(!nextTokenData);
    setLoading(false);
  }

  if (!tokenData) {
    return (
      <div className="flex flex-col items-start gap-2">
        <button
          className="rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          disabled={loading}
          onClick={loadToken}
          type="button"
        >
          {loading ? "Chargement..." : failed ? "Reessayer" : "Connecter une banque"}
        </button>
        {failed ? (
          <p className="text-sm text-red-700">Connexion indisponible.</p>
        ) : null}
      </div>
    );
  }

  return (
    <PlaidLinkButton
      linkToken={
        tokenData.link_token
      }
      reference={tokenData.reference}
    />
  );
}
