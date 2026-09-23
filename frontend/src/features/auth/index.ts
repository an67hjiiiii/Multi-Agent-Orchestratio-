/** Auth and shell entrypoints. Legacy component paths remain stable for consumers. */
export { AuthScreen, AppHeader, NavigationRail } from "../../components/ProductNavigation";
export type { DemoSession, ProductPage } from "../../components/ProductNavigation";
export { authApi } from "./api";
export { toSession } from "./model";
