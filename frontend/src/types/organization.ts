// Organization Types based on backend schemas

export interface OrganizationBase {
  name: string;
  description: string;
}

export interface OrganizationCreate extends OrganizationBase {}

export interface OrganizationUpdate {
  name?: string;
  description?: string;
}

export interface OrganizationInDB extends OrganizationBase {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationResponse extends OrganizationInDB {
  campaign_count: number;
} 