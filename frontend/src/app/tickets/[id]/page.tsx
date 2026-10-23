import { notFound } from "next/navigation";
import { TicketDetail } from "@/components/ticket-detail";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!/^-?\d+$/.test(id) || !Number.isSafeInteger(Number(id))) notFound();
  return <TicketDetail key={id} id={Number(id)} />;
}
