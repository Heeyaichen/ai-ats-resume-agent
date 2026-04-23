import React from "react";
import {
  PublicClientApplication,
  EventType,
  AuthenticationResult,
} from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { msalConfig } from "./authConfig";
import Home from "./Home";

const msalInstance = new PublicClientApplication(msalConfig);

// Initialize MSAL before rendering.
void msalInstance.initialize().then(() => {
  // Handle redirect promise for SSO flows.
  msalInstance.handleRedirectPromise().catch(() => {
    // Silently ignore redirect errors.
  });

  // Set active account on login.
  msalInstance.addEventCallback((event) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
      const payload = event.payload as AuthenticationResult;
      msalInstance.setActiveAccount(payload.account);
    }
  });
});

const App: React.FC = () => (
  <MsalProvider instance={msalInstance}>
    <Home />
  </MsalProvider>
);

export default App;
