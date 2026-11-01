import { refreshAccessToken } from '../utils/appClient';
import { Navigate } from "react-router-dom";

export function formatFriendlyTimestamp(isoString) {
  const alertDate = new Date(isoString);
  const now = new Date();

  const alertDay = alertDate.getDate();
  const alertMonth = alertDate.getMonth();
  const alertYear = alertDate.getFullYear();

  const nowDay = now.getDate();
  const nowMonth = now.getMonth();
  const nowYear = now.getFullYear();

  const timeString = alertDate.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
  if (
    alertDay === nowDay &&
    alertMonth === nowMonth &&
    alertYear === nowYear
  ) {
    return `Today ${timeString}`;
  }
  const yesterday = new Date(now);
  yesterday.setDate(nowDay - 1);

  if (
    alertDay === yesterday.getDate() &&
    alertMonth === yesterday.getMonth() &&
    alertYear === yesterday.getFullYear()
  ) {
    return `Yesterday ${timeString}`;
  }
  const dateString = alertDate.toLocaleDateString([], {
    month: 'short',
    day: 'numeric'
  });

  return `${dateString} ${timeString}`;
}
export function getAuthHeaders() {
  return {
    Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
    'Content-Type': 'application/json'
  };
}

export async function fetchWithRefresh(url, options = {}) {
  let response = await fetch(url, options);

  if (response.status === 403 || response.status === 401) {
    const { refreshAccessToken } = await import('../utils/appClient');
    const newAccessToken = await refreshAccessToken();
    const updatedOptions = {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${newAccessToken}`,
      },
    };

    response = await fetch(url, updatedOptions);
    console.debug(response);
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Error ${response.status}: ${response.statusText}\n${errorText}`);
  }

  return await response.json();
}

export async function fetchWithAuthRetry(url, options = {}) {
let response = await fetch(url, options);
  if (response.status === 403 || response.status === 401) {
    try {
      const newAccessToken = await refreshAccessToken();

      const updatedOptions = {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${newAccessToken}`,
        },
      };

      response = await fetch(url, updatedOptions);
    } catch (refreshError) {
      console.error('Token refresh failed during retry:', refreshError);
      return new Response(null, {
        status: 401,
        statusText: 'Unauthorized',
      });
    }
  }

  return response;
}

export const ROLES = {
  ALL: ['admin', 'operator', 'viewer'],
  ADMIN_ONLY: ['admin'],
};

export function getUserRole() {
  return localStorage.getItem('role');
}
export function hasRole(allowedRoles = []) {
  const role = getUserRole();
  return allowedRoles.includes(role);
}

export const ProtectedRoute = ({ children }) => {
   const isAuthenticated = localStorage.getItem("isAuthenticated") === "true";
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};
export function getDroneStatus(drone) {
  if (!drone) return "N/A";

  if (drone.is_active && drone.is_available && drone.is_in_flight && drone.is_hovering) {
    return "Hovering";
  }
  if (drone.is_active && drone.is_available && drone.is_in_flight && !drone.is_hovering) {
    return "Flight";
  }
  if (drone.is_in_flight) {
    return "Flight";
  }
  if (drone.is_active && drone.is_available) {
    return "Available";
  }
  if (drone.is_active) {
    return "Active";
  }
  return "Inactive";
}