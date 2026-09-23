import { api } from "../../lib/api";

/** Read-only admin routes; this feature does not add authority or mutations. */
export const adminApi = {
  adminStatus: api.adminStatus,
  adminUsers: api.adminUsers,
};
