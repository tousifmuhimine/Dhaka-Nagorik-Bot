export type UserRole = "citizen" | "authority" | "admin";

export type AuthUser = {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  approval_status: "approved" | "pending" | "rejected";
  city_corporation?: string;
  ward_number?: number | null;
  thana?: string | null;
  department?: string;
  employee_id?: string;
  phone_number?: string;
  access_reason?: string;
};

export type LoginResponse = {
  success: boolean;
  user: AuthUser;
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
};

export type SignupResponse = {
  success: boolean;
  message: string;
  user: AuthUser;
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
};
