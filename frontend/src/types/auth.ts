// Authentication Types based on backend schemas

export interface UserSignupRequest {
  email: string;
  password: string;
  confirm_password: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface SignupResponse {
  message: string;
  user: UserResponse;
}

export interface LoginResponse {
  message: string;
  token: TokenResponse;
  user: UserResponse;
}

// Legacy interface for backward compatibility
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

// Legacy interface for backward compatibility  
export interface User extends UserResponse {
  full_name?: string;
  is_active?: boolean;
} 