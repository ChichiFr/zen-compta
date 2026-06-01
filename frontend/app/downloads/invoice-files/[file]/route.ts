import { NextRequest, NextResponse } from "next/server";

import { internalApiToken, requireAuth } from "@/lib/session";

type Params = Promise<{ file: string }>;

function apiBaseUrl() {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return baseUrl.replace(/\/$/, "");
}

export async function GET(
  request: NextRequest,
  { params }: { params: Params },
) {
  await requireAuth();

  const { file } = await params;
  if (file !== "export.csv" && file !== "export.xlsx") {
    return NextResponse.json({ detail: "not_found" }, { status: 404 });
  }

  const upstreamUrl = new URL(`${apiBaseUrl()}/api/invoices/${file}`);
  request.nextUrl.searchParams.forEach((value, key) => {
    upstreamUrl.searchParams.set(key, value);
  });

  const response = await fetch(upstreamUrl, {
    cache: "no-store",
    headers: {
      "X-Internal-API-Token": internalApiToken(),
    },
  });

  return new NextResponse(response.body, {
    status: response.status,
    headers: {
      "Content-Disposition": response.headers.get("Content-Disposition") ?? "",
      "Content-Type": response.headers.get("Content-Type") ?? "text/plain",
    },
  });
}
