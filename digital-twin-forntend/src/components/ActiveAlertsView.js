import React, { useState, useEffect, useRef } from "react";
import "../ActiveAlertsView.css";
import cameraoffIcon from '../images/cameraoff.png';
import { ENDPOINTS } from '../utils/appConfig';
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { updateAlert, fetchActiveAlerts, normalizeStored } from '../utils/appClient';
function ActiveAlertsView({ alerts, setAlerts, setSelectedAlert, setShowDeviceModal }) {
  const [localAlerts, setLocalAlerts] = useState([]);
  const navigate = useNavigate();
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const retryCountRef = useRef(0);
  const [wsConnected, setWsConnected] = useState(false);
  const [showMissionDialog, setShowMissionDialog] = useState(false);
  const [missionData, setMissionData] = useState(null);
  const [showVerifyDialog, setShowVerifyDialog] = useState(false);
  const [verifyAlertId, setVerifyAlertId] = useState(null);
  const [resolutionNotes, setResolutionNotes] = useState("");
  
  useEffect(() => {
    if (missionData) {
      console.log('Mission data updated:', missionData);
    }
  }, [missionData]);
  useEffect(() => {
    fetchActiveAlerts().then(normalized => {
      setLocalAlerts(normalized);
      setAlerts(normalized);
    }).catch(err => console.error('Failed to fetch active alerts', err));
    const test = process.env.REACT_APP_WS_URL;
    console.log("WebSocket URL from env:", test);
    const baseWs = process.env.REACT_APP_WS_URL;
    const wsUrl = baseWs.endsWith('/') ? `${baseWs}ws/alerts/updates/` : `${baseWs}/ws/alerts/updates/`;
    //const wsUrl = "ws://localhost:8001/ws/alerts/updates/"
    const normalizeAlertDevices = (alert) => {
      if (!alert || !Array.isArray(alert.devices) || alert.devices.length === 0) return alert;
      const devices = alert.devices.map((d, i) => ({ ...d, primary_device: i === 0 ? "true" : "false" }));
      return { ...alert, devices };
    };

    const connect = () => {
      try {
        const ws = new WebSocket(wsUrl);
        socketRef.current = ws;
        ws.onopen = () => {
          retryCountRef.current = 0;
          setWsConnected(true);
          console.log("ActiveAlertsView websocket connected");
        };

        ws.onmessage = (event) => {
          try {
            const raw = JSON.parse(event.data);
            console.debug('ActiveAlertsView received raw WS message', raw);
            const type = raw?.type;
            let data = raw?.message || raw?.payload || raw?.data;
            console.debug('ActiveAlertsView normalized WS payload', data);
              if (type === "alert.update") {
                fetchActiveAlerts().then(normalized => {
                  setLocalAlerts(normalized);
                  setAlerts(normalized);
                }).catch(err => console.error('Failed to fetch active alerts', err));
                return;
              }
            if (type === 'drone.alert' || raw?.drone || data?.drone) {
              fetchActiveAlerts().then(normalized => {
                setLocalAlerts(normalized);
                setAlerts(normalized);
              }).catch(err => console.error('Failed to fetch active alerts', err));
              return;
            }
            if (((type === "alert.completed" || type === "alert.complete") || type === 'done.alert') && (data?.alert_id || data?.id)) {
              fetchActiveAlerts().then(normalized => {
                setLocalAlerts(normalized);
                setAlerts(normalized);
              }).catch(err => console.error('Failed to fetch active alerts', err));
              return;
            }
            if (type === "sensor.alert") {
              toast.info(
                <div>
                  Device: {data.sensor_name}<br />
                  Alert Id: {data.sensor_alert_id}
                </div>,
                { autoClose: 20000 }
              );
              return;
            }
            if (type === "drone.complete") {
              fetchActiveAlerts().then(normalized => {
                setLocalAlerts(normalized);
                setAlerts(normalized);
              }).catch(err => console.error('Failed to fetch active alerts', err));
              return;
            }
            if (type === "drone.mission") {
              console.log('Drone mission message received, showing dialog');
              setMissionData(data);
              setShowMissionDialog(true);
              console.log('Mission data set:', data);
              return;
            }
            if (type === "alert.verify" && data?.alert_id) {
              setVerifyAlertId(data.alert_id);
              setShowVerifyDialog(true);
              setResolutionNotes("");
              return;
            }
            console.log('Unhandled WS message in ActiveAlertsView', data);
          } catch (err) {
            console.warn('Failed to parse WS message in ActiveAlertsView', err, event.data);
          }
        };

        ws.onclose = (ev) => {
          setWsConnected(false);
          console.log(`ActiveAlertsView websocket closed (code:${ev.code}). Reconnecting...`);
          retryCountRef.current += 1;
          const delay = Math.min(30000, 1000 * Math.pow(2, retryCountRef.current));
          reconnectTimerRef.current = setTimeout(connect, delay);
        };

        ws.onerror = (err) => {
          console.warn('ActiveAlertsView websocket error', err);
          try { ws.close(); } catch (e) { }
        };

      } catch (e) {
        console.error('ActiveAlertsView websocket setup failed', e);
      }
    };

    connect();

    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (socketRef.current) {
        try { socketRef.current.close(); } catch (e) { }
      }
      socketRef.current = null;
    };
  }, []);
  const handleClosed = async () => {
    try {
      await updateAlert(verifyAlertId, {
        is_resolved: true,
        resolved_at: new Date().toISOString(),
        resolution_notes: resolutionNotes,
        alert_analysis: "Complete"
      });
      toast.success("Alert marked as closed");
    } catch (err) {
      toast.error("Failed to close alert");
    }
    setShowVerifyDialog(false);
  };

  const handleNotClosed = async () => {
    try {
      await updateAlert(verifyAlertId, {
        is_resolved: true,
        resolved_at: new Date().toISOString(),
        resolution_notes: resolutionNotes,
        alert_analysis: "Human Verification",
      });
      toast.success("Alert marked as not closed");
    } catch (err) {
      toast.error("Failed to update alert");
    }
    setShowVerifyDialog(false);
  };

  return (
    <>
      <div className="ws-debug" style={{ padding: '0.5rem 1rem', color: '#ccc', fontSize: '0.9rem' }}>
        WebSocket: <strong style={{ color: wsConnected ? '#7CFC00' : '#FF6347' }}>{wsConnected ? 'connected' : 'disconnected'}</strong>
        &nbsp;|&nbsp; Active alerts: <strong>{(localAlerts || []).filter(a => a.is_active).length}</strong>
      </div>
      <div className="alert-card-grid">
        {(() => {
          const active = (localAlerts || []).filter(a => a.is_active);
          const MAX_VISIBLE = 9;
          const visible = active.slice(0, MAX_VISIBLE);
          return visible.map((alert, index) => {
            if (alert.is_drone) {
              return (
                <DroneCard
                  key={`drone-${alert.id || index}`}
                  alert={alert}
                  setSelectedAlert={setSelectedAlert}
                  setShowDeviceModal={setShowDeviceModal}
                  setLocalAlerts={setLocalAlerts}
                  setAlerts={setAlerts}
                />
              );
            }

            const generatedDevice = (alert.devices || []).find(d => d.primary_device === "true") || (alert.devices && alert.devices.length ? alert.devices[0] : null);
            if (!generatedDevice) {
              console.debug('ActiveAlertsView: alert has no devices, skipping render', alert.id);
              return null;
            }

            return (
              <DeviceCard
                key={`${alert.id}-${generatedDevice.id || index}`}
                alert={alert}
                device={generatedDevice}
                setSelectedAlert={setSelectedAlert}
                setShowDeviceModal={setShowDeviceModal}
              />
            );
          });
        })()}
      </div>
      {showMissionDialog && missionData && (
        <div className="mission-dialog-overlay">
          <div className="mission-dialog">
            <p><strong>Device:</strong> {missionData.device_name}
              <br />
              {missionData.inject_state}</p>
            <div className="mission-dialog-buttons">
              <button onClick={async () => {
                const droneId = missionData?.drone_id;
                if (droneId) {
                  try {
                    const res = await fetch(ENDPOINTS.DRONE_INJECT_APPROVAL(droneId), {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ approved: true })
                    });
                    if (res.ok) {
                      toast.success('Mission approved successfully');
                    } else {
                      toast.error('Failed to approve mission');
                    }
                  } catch (err) {
                    console.error('Error approving mission', err);
                    toast.error('Error approving mission');
                  }
                }
                setShowMissionDialog(false);
                setMissionData(null);
              }}>Approve</button>
              <button onClick={() => {
                setShowMissionDialog(false);
                setMissionData(null);
              }}>Reject</button>
            </div>
          </div>
        </div>
      )}
      {showVerifyDialog && (
        <div className="verify-dialog-overlay">
          <div className="verify-dialog">
            <h3 className="verify-dialog-header">Take Action</h3>
            <textarea
              className="verify-dialog-textarea"
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="Enter resolution notes..."
              rows={4}
            />
            <div className="verify-dialog-buttons-row">
              <button className="verify-btn verify-btn-primary" onClick={handleClosed}>Closed</button>
              <button className="verify-btn verify-btn-primary" onClick={handleNotClosed}>Not Closed</button>
              <button className="verify-btn verify-btn-secondary" onClick={() => setShowVerifyDialog(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function DeviceCard({ alert, device, setSelectedAlert, setShowDeviceModal }) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const cameraId = device.camera?.id;
  const streamUrl = device.video_url === "stream_url" ? ENDPOINTS.CAMERA_STREAM(cameraId) : device.video_url;

  const handleImageClick = () => {
    const url = `/alert-details?alertId=${encodeURIComponent(alert.id)}&type=${alert.type || "camera"}`;
    window.open(url, '_blank');
  };
  return (
    <div className="alert-device-card">
      {(device.primary_device === "true" || device.video_url) && (
        <div className="alert-video-container">
          {isLoading && !hasError && (
            <div className="alert-spinner-wrapper">
              <div className="alert-loader-spinner"></div>
            </div>
          )}

          {!hasError && (
            <img
              src={streamUrl}
              alt={device.camera?.name}
              onLoad={() => setIsLoading(false)}
              onError={() => {
                setIsLoading(false);
                setHasError(true);
              }}
              className={`alert-video-frame ${isLoading ? 'hidden' : ''}`}
              onClick={handleImageClick}
            />
          )}
          {hasError && (
            <div className="error-message text-center" onClick={handleImageClick} role="button" style={{ cursor: 'pointer' }}>
              <img src={cameraoffIcon} alt="Video Off" className="error-icon" />
              <div className="mt-2 text-danger">Failed to stream {device.camera_name}</div>
            </div>
          )}
        </div>
      )}
      <div className="accordion-toggle-wrapper-left">
        <button className="accordion-toggle" onClick={() => setIsExpanded(prev => !prev)}>
          View Details
        </button>
      </div>
      {isExpanded && (
        <div className="device-details-section">
          <h5>Alert Details</h5>
          <div className="custom-alert-details-row">
            <div className="custom-alert-left">
              <div className="custom-timestamp">
                {new Date(device.recorded_at).toLocaleString()}
              </div>
              <div className="custom-description">{alert.message}</div>
            </div>
            <div className="custom-alert-right">
              <div className={`custom-severity-tag severity-${alert.severity?.toLowerCase()}`}>
                {alert.severity?.charAt(0).toUpperCase() + alert.severity?.slice(1).toLowerCase()}
              </div>
              <div className={`custom-status-tag status-${alert.alert_analysis?.toLowerCase()}`}>
                {alert.alert_analysis}
              </div>
            </div>
          </div>

          <h5>Device Details</h5>
          <table className="device-tables">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Timestamp</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(alert.devices || []).map((dev, idx) => (
                <tr key={idx}>
                  <td>{dev.camera.name}</td>
                  <td>{dev.camera.camera_type}</td>
                  <td>{new Date(device.recorded_at).toISOString().replace('T', ' ').slice(0, 19)}</td>
                  <td>{dev.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="inference-breakdown">
            <h5>Inference Breakdown</h5>
            <div className="inference-times">
              <div className="inference-time-item">
                <strong>Start:</strong>
                <div className="inference-value">
                  {alert.start_time ? new Date(alert.start_time).toISOString().slice(11, 19) : '—'}
                </div>
              </div>
              <div className="inference-time-item">
                <strong>End:</strong>
                <div className="inference-value">
                  {alert.end_time ? new Date(alert.end_time).toISOString().slice(11, 19) : '—'}
                </div>
              </div>
            </div>
            <div className="inference-item">
              <strong>Inference Analysis:</strong>
              <div className="inference-value">{alert.inference_analysis || alert.alert_analysis || '—'}</div>
            </div>
            <div className="inference-item">
              <strong>LLM Response:</strong>
              <div className="inference-value">{alert.llm_response || 'No LLM response available.'}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
export default ActiveAlertsView;

function DroneCard({ alert, setSelectedAlert, setShowDeviceModal }) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const drone = alert.drone?.drone || alert.drone || {};
  const flight = alert.drone?.drone_flight || {};
  const cameraId = drone.id;
  const streamUrl = ENDPOINTS.CAMERA_STREAM(cameraId);
  const status = 'Streaming';
  const initialInFlight = !!(
    alert?.is_in_flight ||
    alert?.drone?.is_in_flight ||
    alert?.drone?.drone?.is_in_flight ||
    alert?.drone?.drone?.isInFlight
  );
  const [disabledRTL, setDisabledRTL] = useState(!initialInFlight);
  const [disabledLAND, setDisabledLAND] = useState(!initialInFlight);
  const [disabledMISSION, setDisabledMISSION] = useState(false);
  const navigate = useNavigate();
  const sendDroneCommand = async (cmd) => {
    if (cmd === 'RTL') {
      if (!cameraId) {
        window.alert('Drone id not available');
        return;
      }
      try {
        const url = ENDPOINTS.DRONE_RETURN_TO_LAUNCH(cameraId);
        console.log('Sending RTL to', url);
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
        });

        if (res.ok) {
          setDisabledRTL(true);
          setDisabledLAND(true);
          try { window.alert('RTL command sent successfully'); } catch (e) { }
        } else {
          const text = await res.text();
          console.warn('RTL failed', res.status, text);
          try { window.alert(`RTL failed: ${res.status}`); } catch (e) { }
        }
      } catch (err) {
        console.error('RTL request error', err);
        try { window.alert('RTL request failed'); } catch (e) { }
      }
      return;
    }
    if (cmd === 'LAND') {
      if (!cameraId) {
        window.alert('Drone id not available');
        return;
      }
      try {
        const url = ENDPOINTS.DRONE_EMERGENCY_LAND(cameraId);
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({}),
        });

        if (res.ok) {
          setDisabledLAND(true);
          setDisabledRTL(true);
          try { window.alert('Emergency LAND command sent successfully'); } catch (e) { }
          try { navigate(0); } catch (e) { }
        } else {
          const text = await res.text();
          console.warn('LAND failed', res.status, text);
          try { window.alert(`LAND failed: ${res.status}`); } catch (e) { }
        }
      } catch (err) {
        console.error('LAND request error', err);
        try { window.alert('LAND request failed'); } catch (e) { }
      }
      return;
    }

    if (cmd === 'MISSION') {
      if (!cameraId) {
        window.alert('Drone id not available');
        return;
      }
      try {
        const url = ENDPOINTS.DRONE_INJECT_APPROVAL(cameraId);
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ approved: true }),
        });

        if (res.ok) {
          setDisabledMISSION(true);
          try { window.alert('Mission approval injected successfully'); } catch (e) { }
        } else {
          const text = await res.text();
          console.warn('MISSION failed', res.status, text);
          try { window.alert(`MISSION failed: ${res.status}`); } catch (e) { }
        }
      } catch (err) {
        console.error('MISSION request error', err);
        try { window.alert('MISSION request failed'); } catch (e) { }
      }
      return;
    }
    try { window.alert(`Command "${cmd}" sent to ${drone.name || drone.id}`); } catch (e) { }
  };

  return (
    <div className="alert-device-card">
      <div className="alert-video-container">
        {isLoading && !hasError && (
            <div className="alert-spinner-wrapper">
              <div className="alert-loader-spinner"></div>
            </div>
          )}
        {!hasError && (
          <img
            src={streamUrl}
            alt={drone.name}
            onLoad={() => setIsLoading(false)}
            onError={() => {
              setIsLoading(false);
              setHasError(true);
            }}
            className={`alert-video-frame ${isLoading ? 'hidden' : ''}`}
            style={{ cursor: 'pointer' }}
          />
        )}

        {hasError && (
          <div className="error-message text-center" role="button" style={{ cursor: 'pointer' }}>
            <img src={cameraoffIcon} alt="Video Off" className="error-icon" />
            <div className="mt-2 text-danger">Failed to stream {drone.name}</div>
          </div>
        )}
      </div>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', marginTop: '1rem' }}>
        <div className="accordion-toggle-wrapper-left" style={{ margin: 0, gap: '0.5rem' }}>
          <div>
            <button
              className="accordion-toggle"
              onClick={() => setIsExpanded(prev => !prev)}
            >
              View Details
            </button>
          </div>

          <div>
            <button
              className="accordion-toggle"
              disabled={disabledRTL}
              onClick={() => sendDroneCommand('RTL')}
              title="Return to Launch"
            >
              RTL
            </button>
          </div>

          <div>
            <button
              className="accordion-toggle"
              disabled={disabledLAND}
              onClick={() => sendDroneCommand('LAND')}
              title="Land the drone"
            >
              LAND
            </button>
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="device-details-section">
          <h5>Alert Details</h5>
          <div className="alert-info">
            <div><strong>Device Name:</strong> {flight.device_name || 'N/A'}</div>
            <div><strong>Longitude:</strong> {flight.longitude || drone.longitude || 'N/A'}</div>
            <div style={{ display: 'flex', gap: '2rem' }}>
              <div><strong>Latitude:</strong> {flight.latitude || drone.latitude || 'N/A'}</div>
              <div><strong>Altitude:</strong> {flight.altitude || drone.altitude || 'N/A'}</div>
            </div>

          </div>
          <h5>Device Details</h5>
          <table className="device-tables">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Created At</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{drone.name}</td>
                <td>Drone</td>
                <td>{new Date(drone.created_at || alert.created_at).toISOString().replace('T', ' ').slice(0, 19)}</td>
                <td>{status}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}