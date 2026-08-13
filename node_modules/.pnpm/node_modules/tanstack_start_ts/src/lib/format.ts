export const formatCurrency = (value: number, currency = "BRL") =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: value < 0.1 ? 4 : 2,
  }).format(value);

export const formatTime = (iso: string) =>
  new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));

/** Digits-only currency mask: "150000" -> "1.500,00" */
export const maskCurrencyInput = (raw: string) => {
  const digits = raw.replace(/\D/g, "").slice(0, 11);
  if (!digits) return "";
  const cents = digits.padStart(3, "0");
  const integer = cents.slice(0, -2).replace(/^0+(?=\d)/, "");
  return `${Number(integer).toLocaleString("pt-BR")},${cents.slice(-2)}`;
};

export const parseCurrencyInput = (masked: string) => {
  const digits = masked.replace(/\D/g, "");
  return digits ? Number(digits) / 100 : 0;
};

export const maskDocumentInput = (raw: string) => {
  const d = raw.replace(/\D/g, "").slice(0, 11);
  return d
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/(\d{3})\.(\d{3})\.(\d{3})(\d)/, "$1.$2.$3-$4");
};

export const maskBirthDateInput = (raw: string) => {
  const d = raw.replace(/\D/g, "").slice(0, 8);
  return d.replace(/(\d{2})(\d)/, "$1/$2").replace(/(\d{2})\/(\d{2})(\d)/, "$1/$2/$3");
};