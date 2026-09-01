import React, { createContext, useContext, useState, useEffect } from "react";
import { loginUser, getCurrentUser } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("zydus_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem("zydus_token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function verifyAuth() {
      if (token) {
        try {
          const userData = await getCurrentUser();
          setUser(userData);
          localStorage.setItem("zydus_user", JSON.stringify(userData));
        } catch {
          logout();
        }
      }
      setLoading(false);
    }
    verifyAuth();
  }, [token]);

  const login = async (username, password) => {
    const data = await loginUser(username, password);
    setToken(data.access_token);
    localStorage.setItem("zydus_token", data.access_token);

    const userData = {
      username: username,
      role: data.role || "engineer",
    };
    setUser(userData);
    localStorage.setItem("zydus_user", JSON.stringify(userData));
    return userData;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("zydus_token");
    localStorage.removeItem("zydus_user");
  };

  const role = user?.role || "viewer";
  const isAdmin = role === "admin";
  const isEngineer = role === "engineer" || isAdmin;
  const isAuditor = role === "auditor" || isAdmin;
  const isViewer = role === "viewer";

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        role,
        isAdmin,
        isEngineer,
        isAuditor,
        isViewer,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
