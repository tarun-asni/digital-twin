export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;
export const DEVICE_API_BASE_URL = process.env.REACT_APP_DEVICE_API_BASE_URL;

// Basic Auth credentials
const username = process.env.REACT_APP_API_USERNAME;
const password = process.env.REACT_APP_API_PASSWORD;
export const AUTH_HEADER = 'Basic ' + btoa(`${username}:${password}`);

export const ENDPOINTS = {
  LIVE_FEEDS: `${API_BASE_URL}/command-center/cc-alerts/live-feeds/`,
  CAMERA_DETAILS: (cameraId) => `${API_BASE_URL}/command-center/field-units/cameras/${cameraId}`,
  VOICE_COMMAND: (commandText) =>
    `${API_BASE_URL}/command-center/audio-listener/alerts/?command=${encodeURIComponent(commandText)}`,
  ALERT_DETAILS: (alertId) => `${API_BASE_URL}/command-center/cc-alerts/alerts/${alertId}/`,
  DEVICE_LIST: `${API_BASE_URL}/command-center/field-units/devices`,
  DEVICE_DETAIL: (deviceId) => `${API_BASE_URL}/command-center/field-units/device/${deviceId}`,
  DEVICE_ORDER: `${DEVICE_API_BASE_URL}/device_order`,
  DEVICE_CONFIG_PUT:(deviceId)=> `${API_BASE_URL}/command-center/device-config/settings/${deviceId}/`,
  DEVICE_CONFIG_POST : `${API_BASE_URL}/command-center/device-config/settings/`, 
  DEVICE_CONFIG : (deviceId)=> `${API_BASE_URL}//command-center/device-config/settings/${deviceId}/device/`, 
  LOGIN: `${API_BASE_URL}/command-center/user-auth/login/`,
  REFRESH_TOKEN: `${API_BASE_URL}/command-center/user-auth/token/refresh/`,
  AUTH_LIST: `${API_BASE_URL}/command-center/user-auth/auth/`,
  AUTH_LIST_UPDATE:(Id)=> `${API_BASE_URL}/command-center/user-auth/auth/${Id}/`,
  USER_ROLES: `${API_BASE_URL}/command-center/user-auth/role/`,
  ROLE_LIST: `${API_BASE_URL}/command-center/user-auth/role/`,
  ALERT_LIST: `${API_BASE_URL}/command-center/cc-alerts/alerts/`,
  ACTIVE_ALERTS: `${API_BASE_URL}/command-center/cc-alerts/alerts/active-alerts/`,
  CAMERA_STREAM: (cameraId) =>
  `${API_BASE_URL}/command-center/cc-alerts/camera/${cameraId}/stream/?annotate=False`,
  DRONE_RETURN_TO_LAUNCH: (droneId) => `${API_BASE_URL}/command-center/field-units/drones/${droneId}/return_to_launch/`,
  DRONE_EMERGENCY_LAND: (droneId) => `${API_BASE_URL}/command-center/field-units/drones/${droneId}/emergency_land/`,
  DRONE_INJECT_APPROVAL: (droneId) => `${API_BASE_URL}/command-center/field-units/drones/${droneId}/inject_approval/`,
  SENSOR_ALERTS: `${API_BASE_URL}/command-center/cc-alerts/sensor-alerts/`,
  ALERT_UPDATE: (alertId) => `${API_BASE_URL}/command-center/cc-alerts/alerts/${alertId}/update/`,
  SENSOR_ALERT_DETAILS: (sensorAlertId) =>`${API_BASE_URL}/command-center/cc-alerts/sensor-alerts/${sensorAlertId}/`,
};