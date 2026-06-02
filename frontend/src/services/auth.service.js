import { authAPI } from '../lib/api';

export const authService = {
  login: authAPI.login,
  logout: authAPI.logout,
  getProfile: authAPI.getProfile,
  refreshToken: authAPI.refreshToken
}; 