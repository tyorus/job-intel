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
