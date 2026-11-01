import { ENDPOINTS, AUTH_HEADER } from '../utils/appConfig';
import { getAuthHeaders } from '../utils/Helpers';
import { fetchWithAuthRetry } from '../utils/Helpers';
import { toast } from "react-toastify";


export async function fetchLiveFeeds() {
  try {
      let response = await fetchWithAuthRetry(ENDPOINTS.LIVE_FEEDS, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch live feeds:', error);
    throw error;
  }
}

export async function fetchCameraDetails(cameraId) {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.CAMERA_DETAILS(cameraId), {
      method: 'GET',
      headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch camera details:', error);
    throw error;
  }
}

export async function sendVoiceCommand(commandText) {
  try {
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const headers = {
      ...getAuthHeaders(),
      'X-User-Timezone': userTimezone,
    };
    const response = await fetchWithAuthRetry(ENDPOINTS.VOICE_COMMAND(commandText), {
      method: 'GET',
      headers: headers,
    });
    if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
    return await response.json();
  } catch (error) {
    console.error('Failed to send voice command:', error);
    if (error?.message?.includes('404')) {
      return [];
    }
    return null;
  }

}
export async function fetchAlertDetails(alertId) {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.ALERT_DETAILS(alertId));
    if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch alert details:', error);
    throw error;
  }
}
export async function fetchDeviceList() {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.DEVICE_LIST, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch device list:', error);
    throw error;
  }
}
export async function submitDeviceOrder(name, type) {
  try {
    const response = await fetch(ENDPOINTS.DEVICE_ORDER, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, type }),
    });

    if (response.status === 409) {
      return {
        success: false,
        error: `Device with name '${name}' already exists.`,
      };
    }

    if (!response.ok) throw new Error('Download failed');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name.replace(/\s+/g, '_')}_device.zip`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    return { success: true };
  } catch (error) {
    console.error('Failed to submit device order:', error);
    return {
      success: false,
      error: 'Failed to submit device order.',
    };
  }
}
export async function loginUser(username, password) {
  try {
    const response = await fetch(ENDPOINTS.LOGIN, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
   
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Login failed');
    }
     
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Login failed:', error);
    throw error;
  }
}
export async function refreshAccessToken() {
  try {
    const refreshToken = localStorage.getItem('refreshToken');

    const response = await fetch(ENDPOINTS.REFRESH_TOKEN, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    const contentType = response.headers.get('content-type');
    let data;

    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } 
    if (!response.ok) {
      console.error("Refresh failed:", data);
      throw new Error(data.detail || 'Failed to refresh token');
    }

    if (data.access) localStorage.setItem('accessToken', data.access);
    if (data.refresh) localStorage.setItem('refreshToken', data.refresh);

    return data.access;
  } catch (error) {
    console.error('Token refresh failed:', error);
    throw error;
  }
}
export async function fetchAuthList() {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.AUTH_LIST, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch auth profile:', error);
    throw error;
  }
}

export async function fetchRoles() {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.ROLE_LIST, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to fetch roles:', error);
    throw error;
  }
}
export async function registerUser(payload) {
  try {
    let response = await fetch(ENDPOINTS.AUTH_LIST, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (response.status === 401 || response.status === 403) {
      console.warn('Access token expired. Attempting to refresh...');
      const newAccessToken = await refreshAccessToken();
      response = await fetch(ENDPOINTS.AUTH_LIST, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          Authorization: `Bearer ${newAccessToken}`
        },
        body: JSON.stringify(payload)
      });
    }
return response
  } catch (error) {
    toast.error(error.message || "Failed to register user.");
    throw error;
  }
}


export async function UpdateUser(payload) {
  try {
    let response = await fetch(ENDPOINTS.AUTH_LIST_UPDATE(payload.id), {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (response.status === 401 || response.status === 403) {
      console.warn('Access token expired. Attempting to refresh...');
      const newAccessToken = await refreshAccessToken();
      response = await fetch(ENDPOINTS.AUTH_LIST_UPDATE(payload.id), {
        method: 'PATCH',
        headers: {
          ...getAuthHeaders(),
          Authorization: `Bearer ${newAccessToken}`
        },
        body: JSON.stringify(payload)
      });
    }

    
    return response;

  } catch (error) {
    toast.error(error.message || "Failed to update user.");
    throw error;
  }
}
export async function fetchDeviceConfiguration(deviceId) {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.DEVICE_CONFIG(deviceId), {
      method: 'GET',
      headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch device list:', error);
    throw error;
  }
}
export async function fetchDeviceDetail(deviceId) {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.DEVICE_DETAIL(deviceId), {
      method: 'GET',
      headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch device list:', error);
    throw error;
  }
}
export async function fetchAlertsList() {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.ALERT_LIST, {
      method: "GET",
       headers: getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data || [];
  } catch (error) {
    console.error("Failed to fetch camera alerts:", error);
    throw error;
  }
}
export async function fetchSensorAlerts() {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.SENSOR_ALERTS, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    return data || [];
  } catch (error) {
    console.error("Failed to fetch sensor alerts:", error);
    throw error;
  }
}
export async function updateAlert(alertId, payload) {
  try {
    const response = await fetchWithAuthRetry(ENDPOINTS.ALERT_UPDATE(alertId), {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => null);
      throw new Error(errData?.detail || `Error ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to update alert:', error);
    throw error;
  }
}
export async function fetchSensorAlertDetails(sensorAlertId) {
  try {
    const response = await fetchWithAuthRetry(
      ENDPOINTS.SENSOR_ALERT_DETAILS(sensorAlertId),
      {
        method: "GET",
        headers: getAuthHeaders(),
      }
    );
    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }
    const sensorData = await response.json();
    const normalized = {
      id: sensorData.sensor_alert,
      type: "sensor",
      sensor_id: sensorData.sensor_id,
      drone_id: sensorData.drone_id,
      drone_flight_id: sensorData.drone_flight_id,
      message: sensorData.description,
      start_time: sensorData.timestamp,
      alert_analysis: sensorData.status,
      title: sensorData.description || "Sensor Alert",
      severity: sensorData.severity,
      llm_response: sensorData.llm_response,
      drone: {
        id: sensorData?.drone?.id,
        name: sensorData?.drone?.name,
        model: sensorData?.drone?.model,
        manufacturer: sensorData?.drone?.manufacturer,
        serial_number: sensorData?.drone?.serial_number,
        latitude: sensorData?.drone?.latitude,
        longitude: sensorData?.drone?.longitude,
        altitude: sensorData?.drone?.altitude,
        is_active: sensorData?.drone?.is_active,
        installation_date: sensorData?.drone?.installation_date,
        last_maintenance: sensorData?.drone?.last_maintenance,
        notes: sensorData?.drone?.notes,
        drone_type: sensorData?.drone?.drone_type,
        is_in_flight: sensorData?.drone?.is_in_flight,
        battery_percentage: sensorData?.drone?.battery_percentage,
        camera_specs: sensorData?.drone?.camera_specs,
        gps_enabled: sensorData?.drone?.gps_enabled,
        obstacle_avoidance: sensorData?.drone?.obstacle_avoidance,
        autonomous_flight: sensorData?.drone?.autonomous_flight,
        weather_resistance: sensorData?.drone?.weather_resistance,
        edge_url: sensorData?.drone?.edge_url,
      },
      devices: (sensorData?.devices || []).map(device => ({
        id: device?.device_id,
        device_name: device?.device_name,
        primary: device?.primary_device,
        status: device?.status,
        start_time: device?.recording_start,
        end_time: device?.recording_end,
        video_url: device?.video_url,
      }))
    };
    return normalized;
  } catch (error) {
    console.error("Failed to fetch sensor alert details:", error);
    throw error;
  }
}

export const normalizeStored = (arr) => arr.map(item => {
  if (item?.type === 'drone.alert' && item?.message) {
    const msg = item.message;
    return {
      id: msg.id || msg.serial_number || item.id,
      is_drone: true,
      drone: msg,
      is_active: msg.is_active !== undefined ? msg.is_active : true,
      video_url: msg.video_url || msg.stream_url || null,
      created_at: msg.created_at || msg.updated_at || new Date().toISOString(),
    };
  }
  if (item?.drone) {
    const d = item.drone;
    return {
      ...item,
      id: item.id || d.id || d.serial_number,
      is_drone: true,
      is_active: item.is_active !== undefined ? item.is_active : (d.is_active !== undefined ? d.is_active : true),
      video_url: item.video_url || d.video_url || d.stream_url || null,
      drone: d,
      type: "sensor",
    };
  }
  return item;
});

export const fetchActiveAlerts = async () => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    try {
      const res = await fetch(ENDPOINTS.ACTIVE_ALERTS, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const alerts = data.alerts_data || [];
      const droneAlerts = (data.sensor_alerts_data || []).map(d => ({
        id: d.drone.id || d.drone.serial_number,
        is_drone: true,
        drone: { ...d.drone, drone_flight: d.drone_flight },
        is_active: d.drone.is_active,
        video_url: d.drone.video_url || d.drone.stream_url || null,
        created_at: d.drone.created_at || d.drone.updated_at || new Date().toISOString(),
      }));
      const allAlerts = [...alerts, ...droneAlerts];
      const normalized = normalizeStored(allAlerts);
      return normalized;
    } catch (err) {
      console.error('Failed to fetch active alerts', err);
      return [];
    }
  }
  return [];
};