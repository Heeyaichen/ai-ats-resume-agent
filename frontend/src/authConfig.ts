/** MSAL configuration for Microsoft Entra ID auth. */

import { Configuration, LogLevel } from "@azure/msal-browser";

export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || "",
    authority:
      import.meta.env.VITE_AZURE_AUTHORITY ||
      "https://login.microsoftonline.com/common",
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (_level: LogLevel, message: string) => {
        console.log(`[MSAL] ${message}`);
      },
      logLevel: LogLevel.Warning,
    },
  },
};

export const loginRequest = {
  scopes: [import.meta.env.VITE_API_SCOPE || "api://default/access_as_user"],
};
