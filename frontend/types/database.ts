// TypeScript types mirroring the Supabase database schema (current_db.sql)

export type Severity = "low" | "medium" | "high" | "critical";
export type Status = "investigating" | "confirmed" | "resolved";
export type AttackVector =
  | "phishing"
  | "ransomware"
  | "api_exploit"
  | "insider"
  | "supply_chain"
  | "misconfiguration"
  | "malware"
  | "ddos"
  | "other";
export type UpdateType =
  | "discovery"
  | "new_info"
  | "class_action"
  | "regulatory_fine"
  | "remediation"
  | "resolution"
  | "investigation";
export type TagType =
  | "continent"
  | "country"
  | "industry"
  | "attack_vector"
  | "cve"
  | "mitre_attack"
  | "threat_actor";

export interface Breach {
  id: string;
  company: string;
  industry: string | null;
  country: string | null;
  continent: string | null;
  discovery_date: string | null;
  disclosure_date: string | null;
  records_affected: number | null;
  breach_method: string | null;
  attack_vector: AttackVector | null;
  data_compromised: string[];
  severity: Severity | null;
  status: Status;
  threat_actor: string | null;
  cve_references: string[];
  mitre_techniques: string[];
  summary: string | null;
  lessons_learned: string | null;
  created_at: string;
  updated_at: string;
}

export interface BreachSummary extends Breach {
  update_count: number;
  source_count: number;
  last_update_date: string | null;
}

export interface BreachUpdate {
  id: string;
  breach_id: string;
  update_date: string;
  update_type: UpdateType;
  description: string;
  source_url: string | null;
  extracted_data: Record<string, unknown> | null;
  confidence_score: number | null;
  ai_reasoning: string | null;
  created_at: string;
}

export interface BreachTag {
  id: string;
  breach_id: string;
  tag_type: TagType;
  tag_value: string;
  created_at: string;
}

export interface Source {
  id: string;
  breach_id: string;
  url: string;
  title: string | null;
  published_date: string | null;
  created_at: string;
}

export interface CompanyAlias {
  id: string;
  breach_id: string;
  alias: string;
  is_primary: boolean;
  created_at: string;
}

export interface TagCount {
  tag_type: TagType;
  tag_value: string;
  breach_count: number;
}

export interface BreachDetail extends Breach {
  updates: BreachUpdate[];
  tags: BreachTag[];
  sources: Source[];
}
