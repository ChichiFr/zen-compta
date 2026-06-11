import type { StatusMessage } from "@/app/pageUtils";

const STATUS_MESSAGE_STYLES = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  review: "border-amber-200 bg-amber-50 text-amber-950",
  technical: "border-rose-200 bg-rose-50 text-rose-900",
};

export function StatusMessageBanner({ message }: { message: StatusMessage }) {
  return (
    <p
      className={`rounded-md border px-4 py-3 text-sm font-medium ${STATUS_MESSAGE_STYLES[message.kind]}`}
    >
      {message.text}
    </p>
  );
}
