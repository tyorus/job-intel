export const JOB_STATUSES = [
  "new",
  "analyzed",
  "shortlisted",
  "cv_ready",
  "applied",
  "interview",
  "offer",
  "rejected",
  "archived",
  "not_related",
];

export const PROSPECT_STATUSES = [
  "new",
  "contacted",
  "replied",
  "call_booked",
  "proposal",
  "won",
  "lost",
  "nurture",
  "cancelled",
];

export const POST_STATUSES = ["idea", "draft", "scheduled", "published", "archived"];

export const POST_CHANNELS = ["web", "linkedin"];

export const MEDIA_KINDS = ["image", "video", "document"];

export const PACKAGES = ["unknown", "audit", "brief", "retainer"];

export const PACKAGE_LABELS = {
  unknown: "Unspecified",
  audit: "Workflow audit",
  brief: "Operational brief",
  retainer: "Monthly retainer",
};

export const STATUS_LABELS = {
  not_related: "Not related",
  call_booked: "Call booked",
  cv_ready: "CV ready",
  cancelled: "Cancelled",
};

export function formatWhen(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function labelize(value) {
  if (!value) return "";
  if (STATUS_LABELS[value]) return STATUS_LABELS[value];
  return String(value).replaceAll("_", " ");
}

export function isPastDeadline(value) {
  if (!value) return false;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return false;
  return date.getTime() < Date.now();
}

export function sortMark(activeKey, key, dir) {
  if (activeKey !== key) return "";
  return dir === "asc" ? " ↑" : " ↓";
}

export function defaultSortDir(key) {
  if (["title", "company", "name", "deadline", "follow_up", "published"].includes(key)) return "asc";
  return "desc";
}

export function sortBy(rows, key, dir, getters) {
  const getter = getters[key];
  if (!getter) return rows;
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const va = getter(a);
    const vb = getter(b);
    const aEmpty = va == null || va === "";
    const bEmpty = vb == null || vb === "";
    if (aEmpty && bEmpty) return 0;
    if (aEmpty) return 1;
    if (bEmpty) return -1;
    if (typeof va === "number" && typeof vb === "number") return (va - vb) * sign;
    const sa = String(va).toLowerCase();
    const sb = String(vb).toLowerCase();
    if (sa < sb) return -1 * sign;
    if (sa > sb) return 1 * sign;
    return 0;
  });
}
