export function todayISO(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60_000).toISOString().slice(0, 10);
}

export function formatDate(value: string): string {
  const date = new Date(`${value}T12:00:00`);
  return new Intl.DateTimeFormat("tr-TR", {
    day: "numeric",
    month: "long",
    weekday: "short",
  }).format(date);
}

export function formatDistance(meters: number): string {
  if (!meters) return "0 km";
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}

export function formatDuration(seconds: number): string {
  if (!seconds) return "0 dk";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} dk`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} sa ${rest} dk` : `${hours} sa`;
}

export function formatClock(minutes: number | null): string {
  if (minutes === null || minutes === undefined) return "—";
  const h = Math.floor(minutes / 60) % 24;
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function minutesToTime(minutes: number): string {
  return formatClock(minutes);
}

export function timeToMinutes(value: string): number {
  const [hour, minute] = value.split(":").map(Number);
  return hour * 60 + minute;
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    unassigned: "Sevkiyat Bekliyor",
    assigned: "Güzergâhta",
    delivered: "Teslim edildi",
    failed: "Teslim edilemedi",
    pending: "Bekliyor",
    draft: "Taslak",
    published: "Yolda",
    completed: "Tamamlandı",
    dispatcher: "Kervanbaşı",
    driver: "Sâik",
  };
  return labels[status] ?? status;
}
