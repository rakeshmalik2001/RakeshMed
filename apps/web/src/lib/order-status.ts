"use client";

type OrderPaymentMethod = "UPI" | "CARD" | "COD" | "WALLET";

type OrderPaymentSnapshot = {
  payment_method: OrderPaymentMethod;
  payment_status: string;
  status: string;
};

export function formatOrderStatusLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function getPaymentStatusLabel(method: OrderPaymentMethod, status: string) {
  if (method === "COD") {
    return "Cash on Delivery selected";
  }

  const methodLabel =
    method === "UPI" ? "UPI" : method === "CARD" ? "Card" : method === "WALLET" ? "Wallet" : "Online";

  if (status === "paid") {
    return `${methodLabel} payment confirmed`;
  }

  if (status === "failed") {
    return `${methodLabel} payment failed`;
  }

  return `${methodLabel} payment pending confirmation`;
}

export function isOrderAwaitingPaymentUpdate(order: OrderPaymentSnapshot | null | undefined) {
  if (!order) {
    return false;
  }

  return order.payment_method !== "COD" && order.payment_status !== "paid" && order.status !== "cancelled";
}

export function getPaymentStatusDescription(order: OrderPaymentSnapshot | null | undefined) {
  if (!order) {
    return "Payment status will appear once the order is created.";
  }

  if (order.payment_method === "COD") {
    return "No online payment confirmation is needed for this order.";
  }

  if (order.payment_status === "paid") {
    return "The gateway has confirmed this payment.";
  }

  if (order.payment_status === "failed") {
    return "This payment attempt did not complete. Create a fresh payment link to try again.";
  }

  return "The order is recorded and payment confirmation is still in progress.";
}
