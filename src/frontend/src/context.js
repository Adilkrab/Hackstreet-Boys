import { createContext, useContext } from "react";

// Shared app state: current role, notifications and a refresh signal.
export const AppContext = createContext(null);
export const useApp = () => useContext(AppContext);
