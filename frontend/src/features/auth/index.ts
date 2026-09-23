/** Auth and shell entrypoints. Legacy component paths remain stable for consumers. */
export { AuthScreen, AppHeader, NavigationRail } from "../../components/ProductNavigation";
export type { DemoSession, ProductPage, ViewMode } from "../../components/ProductNavigation";
export { authApi } from "./api";
export {
  authRestoreState,
  hasRememberedSession,
  rememberSession,
  toSession,
} from "./model";
export type { AuthRestoreState } from "./model";
