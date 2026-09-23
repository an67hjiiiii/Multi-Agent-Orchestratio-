import { api } from "../../lib/api";

/** Auth-only API surface for the product shell. */
export const authApi = {
  authSession: api.authSession,
  register: api.register,
  login: api.login,
  logout: api.logout,
};
