import type { AttackVector, Severity, Status, UpdateType, TagType } from "@/types/database";

export const SEVERITY_COLORS: Record<Severity, string> = {
  critical: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
  medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  low: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
};

export const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

export const STATUS_COLORS: Record<Status, string> = {
  investigating: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  confirmed: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  resolved: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
};

export const STATUS_LABELS: Record<Status, string> = {
  investigating: "Investigating",
  confirmed: "Confirmed",
  resolved: "Resolved",
};

export const ATTACK_VECTOR_LABELS: Record<AttackVector, string> = {
  phishing: "Phishing",
  ransomware: "Ransomware",
  api_exploit: "API Exploit",
  insider: "Insider Threat",
  supply_chain: "Supply Chain",
  misconfiguration: "Misconfiguration",
  malware: "Malware",
  ddos: "DDoS",
  other: "Other",
};

export const UPDATE_TYPE_LABELS: Record<UpdateType, string> = {
  discovery: "Discovery",
  new_info: "New Information",
  class_action: "Class Action",
  regulatory_fine: "Regulatory Fine",
  remediation: "Remediation",
  resolution: "Resolution",
  investigation: "Investigation",
};

export const TAG_TYPE_LABELS: Record<TagType, string> = {
  continent: "Continent",
  country: "Country",
  industry: "Industry",
  attack_vector: "Attack Vector",
  cve: "CVE",
  mitre_attack: "MITRE ATT&CK",
  threat_actor: "Threat Actor",
};

export const RSS_SOURCES = [
  { name: "BleepingComputer", url: "https://www.bleepingcomputer.com" },
  { name: "The Hacker News", url: "https://thehackernews.com" },
  { name: "DataBreachToday", url: "https://www.databreachtoday.co.uk" },
  { name: "Krebs on Security", url: "https://krebsonsecurity.com" },
  { name: "HelpNet Security", url: "https://www.helpnetsecurity.com" },
  { name: "NCSC UK", url: "https://www.ncsc.gov.uk" },
  { name: "Check Point Research", url: "https://research.checkpoint.com" },
  { name: "Have I Been Pwned", url: "https://haveibeenpwned.com" },
];
