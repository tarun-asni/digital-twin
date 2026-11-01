import React, { useState, useEffect } from "react";
import "../ActiveAlertsView.css";
import cameraoffIcon from "../images/cameraoff.png";
import securityIcon from "../images/security-cameras.png";
import Sidebar from "../components/SideBar";
import { hasRole, ROLES } from "../utils/Helpers";
import { ENDPOINTS } from '../utils/appConfig';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchAlertDetails } from '../utils/appClient';
import { toast } from "react-toastify";

function AlertDetailPage({ alert, onClose }) {
    const [localAlert, setLocalAlert] = useState(null);
    const [deviceStates, setDeviceStates] = useState([]);
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [expandedCards, setExpandedCards] = useState({});
    const username = localStorage.getItem("username");
    const { alertId } = useParams();
    const [isFetching, setIsFetching] = useState(false);
    const [disabledRTL, setDisabledRTL] = useState(false);
    const [disabledLAND, setDisabledLAND] = useState(false);
    const handleSignOut = () => {
        localStorage.clear();
        window.location.href = "/login";
    };
    const hasRoleFn = (allowedRoles) => {
        const role = localStorage.getItem("role");
        return allowedRoles.includes(ROLES.ALL) || allowedRoles.includes(role);
    };
    useEffect(() => {
        let mounted = true;

        async function loadAlert() {
            if (alert) {
                setLocalAlert(alert);
                return;
            }

            if (alertId) {
                try {
                    setIsFetching(true);
                    const data = await fetchAlertDetails(alertId);
                    if (mounted) setLocalAlert(data);
                } catch (e) {
                    console.error('Failed to fetch alert by id', e);
                } finally {
                    if (mounted) setIsFetching(false);
                }
            }
        }

        loadAlert();

        return () => {
            mounted = false;
        };
    }, [alert, alertId]);
    useEffect(() => {
        const activeAlert = alert || localAlert;
        if (activeAlert?.devices?.length) {
            setDeviceStates((activeAlert.devices || []).map(() => ({ isLoading: true, hasError: false })));
        } else {
            setDeviceStates([]);
        }
    }, [alert, localAlert]);

    const currentAlert = alert || localAlert;
    if (!currentAlert) {
        return (
            <div style={{ padding: 24 }}>
                <h3>Alert Detail</h3>
                <p>No alert selected. Open an alert from the dashboard to view details.</p>
            </div>
        );
    }
    const filteredDevices = currentAlert.type === "sensor"
        ? (currentAlert.devices || []).filter(d => !d.primary)
        : (currentAlert.devices || []);

    const handleLoad = index => {
        setDeviceStates(prev =>
            prev.map((state, i) => (i === index ? { ...state, isLoading: false } : state))
        );
    };

    const handleError = index => {
        setDeviceStates(prev =>
            prev.map((state, i) =>
                i === index ? { ...state, isLoading: false, hasError: true } : state
            )
        );
    };

    const toggleExpand = index => {
        setExpandedCards(prev => ({
            ...prev,
            [index]: !prev[index]
        }));
    };

    const sendDroneCommand = async (cmd) => {
        const currentAlertData = alert || localAlert;
        if (!currentAlertData?.drone) {
            window.alert('Drone information not available');
            return;
        }
        const droneId = currentAlertData.drone?.id;
        if (cmd === 'RTL') {
            if (!droneId) {
                window.alert('Drone id not available');
                return;
            }
            try {
                const url = ENDPOINTS.DRONE_RETURN_TO_LAUNCH(droneId);
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
                    toast.success('RTL command sent successfully');
                } else {
                    const text = await res.text();
                    console.warn('RTL failed', res.status, text);
                    toast.error(`RTL failed: ${res.status}`);
                }
            } catch (err) {
                console.error('RTL request error', err);
                toast.error('RTL request failed');
            }
            return;
        }
        if (cmd === 'LAND') {
            if (!droneId) {
                window.alert('Drone id not available');
                return;
            }
            try {
                const url = ENDPOINTS.DRONE_EMERGENCY_LAND(droneId);
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
                    toast.success('Emergency LAND command sent successfully');
                } else {
                    const text = await res.text();
                    console.warn('LAND failed', res.status, text);
                    toast.error(`LAND failed: ${res.status}`);
                }
            } catch (err) {
                console.error('LAND request error', err);
                toast.error('LAND request failed');
            }
            return;
        }
    };

    return (
        <div
            className="alert-wrapper"
            style={{
                display: "grid",
                gridTemplateColumns: isSidebarOpen ? "240px 1fr" : "0px 1fr",
                gridTemplateRows: "auto 1fr",
                height: "100vh",
                overflow: "hidden"
            }}
        >
            <Sidebar
                username={username}
                handleSignOut={handleSignOut}
                hasRole={hasRoleFn}
                title=""
                collapsed={!isSidebarOpen}
                style={{ gridRow: "1 / span 2", gridColumn: "1" }}
            />

            <div className="top-nav-bar d-flex align-items-center px-3 py-2 gap-2" style={{ gridColumn: "2", gridRow: "1" }}>
                <button
                    className="btn btn-link text-white p-0 icon-only"
                    onClick={() => setIsSidebarOpen(prev => !prev)}
                    title={isSidebarOpen ? "Close Menu" : "Open Menu"}
                    aria-label="Toggle Sidebar"
                >
                    <img src={securityIcon} alt="Toggle Sidebar" className="sidebar-toggle-icon" />
                </button>
                <span className="text-white fw-semibold user-header-title">Alert Detail View</span>
            </div>

            {/* Device Cards */}
            <div className="alert-card-grid alert-detail-grid" style={{ gridColumn: "2", gridRow: "2" }}>
                {filteredDevices.map((device, index) => {
                    const cameraId = device.camera?.id || device.camera_id || device.id;
                    const streamUrl = (device.video_url === "stream_url" || !device.video_url)
                        ? (cameraId ? ENDPOINTS.CAMERA_STREAM(cameraId) : '')
                        : device.video_url;
                    const { isLoading, hasError } = deviceStates[index] || {};

                    return (
                        <div key={`${currentAlert.id}-${device.id || index}`} className="alertdetails-device-card">
                            {/* Live Feed */}
                            <div className="alert-video-container">
                                {isLoading && !hasError && <div className="alert-spinner-wrapper">
                                    <div className="alert-loader-spinner"></div>
                                </div>}
                                {!hasError && (
                                    currentAlert.alert_analysis?.toLowerCase() !== "active" ? (
                                        <video
                                            src={
                                                device.video_url && device.video_url !== "stream_url"
                                                    ? `${process.env.REACT_APP_API_BASE_URL}${device.video_url}`
                                                    : streamUrl
                                            }
                                            controls
                                            className="alert-video-player"
                                            onLoadedData={() => handleLoad(index)}
                                            onError={() => handleError(index)}
                                        />
                                    ) : (
                                        <img
                                            src={streamUrl}
                                            alt={device.camera?.name || "Live Camera"}
                                            className="alert-video-frame"
                                            onLoad={() => handleLoad(index)}
                                            onError={() => handleError(index)}
                                        />
                                    )
                                )}
                                {hasError && (
                                    <div className="alert-spinner-wrapper">
                                        <div className="error-message text-center" aria-live="polite">
                                            <img src={cameraoffIcon} alt="Video Off" className="error-icon" />
                                            <div className="mt-2 text-danger">
                                                {(currentAlert.alert_analysis?.toLowerCase() !== "active" &&
                                                    (device.video_url === "stream_url" || device.video_url == null))
                                                    ? `Video not available ${currentAlert.type === "sensor"
                                                        ? device?.device_name
                                                        : device?.camera_name
                                                    }`
                                                    : `Failed to stream ${currentAlert.type === "sensor"
                                                        ? device?.device_name
                                                        : device?.camera_name
                                                    }`}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                            <div className="accordion-toggle-wrapper-left" style={currentAlert.type === "sensor" ? { gap: '0.5rem' } : {}}>
                                <button className="accordion-toggle" onClick={() => toggleExpand(index)}>
                                    View Details
                                </button>
                                {currentAlert.type === "sensor" && (
                                    <>
                                        <button
                                            className="accordion-toggle"
                                            disabled={disabledRTL}
                                            onClick={() => sendDroneCommand('RTL')}
                                            title="Return to Launch"
                                        >
                                            RTL
                                        </button>
                                        <button
                                            className="accordion-toggle"
                                            disabled={disabledLAND}
                                            onClick={() => sendDroneCommand('LAND')}
                                            title="Land the drone"
                                        >
                                            LAND
                                        </button>
                                    </>
                                )}
                            </div>
                            {expandedCards[index] && (
                                <div className="device-details-section">
                                    <h5>Alert Details</h5>
                                    <div className="custom-alert-details-row">
                                        <div className="custom-alert-left">
                                            <div className="custom-timestamp">
                                                {currentAlert.type === "sensor"
                                                    ? (currentAlert?.start_time
                                                        ? new Date(currentAlert.start_time).toISOString().replace("T", " ").slice(0, 19)
                                                        : "N/A")
                                                    : (device?.recorded_at
                                                        ? new Date(device.recorded_at).toISOString().replace("T", " ").slice(0, 19)
                                                        : "N/A")}
                                            </div>
                                            <div className="custom-description">{alert.message}</div>
                                        </div>
                                        <div className="custom-alert-right">
                                            <div className={`custom-severity-tag severity-${alert.severity?.toLowerCase()}`} style={{ width: 'fit-content' }}>
                                                {alert.severity?.charAt(0).toUpperCase() + alert.severity?.slice(1).toLowerCase()}
                                            </div>
                                            <div className={`custom-status-tag status-${alert.alert_analysis?.toLowerCase()}`} style={{ width: 'fit-content' }}>
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
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                {currentAlert.type !== "sensor" ? (
                                                    <>
                                                        <td>{device.camera?.name || "N/A"}</td>
                                                        <td>{device.camera?.camera_type || "N/A"}</td>
                                                    </>
                                                ) : (
                                                    <>
                                                        <td>{device?.device_name || "N/A"}</td>
                                                        <td>{"DRONE"}</td>
                                                    </>
                                                )}

                                                <td>{device.status}</td>
                                            </tr>
                                        </tbody>
                                    </table>

                                    {currentAlert.type === "sensor" && (
                                        <div className="alert-info">
                                            <div><strong>Longitude:</strong> {currentAlert.drone?.longitude || 'N/A'}</div>
                                            <div><strong>Latitude:</strong> {currentAlert.drone?.latitude || 'N/A'}</div>
                                            <div><strong>Altitude:</strong> {currentAlert.drone?.altitude || 'N/A'}</div>
                                        </div>
                                    )}
                                    <div className="inference-breakdown">
                                        <h5>Inference Breakdown</h5>
                                        <div className="inference-times">
                                            <div className="inference-time-item">
                                                <strong>Start:</strong>
                                                <div className="inference-value">
                                                    {currentAlert.type === "sensor"
                                                        ? (device?.start_time
                                                            ? new Date(device.start_time).toISOString().slice(11, 19)
                                                            : '—')
                                                        : (currentAlert.start_time
                                                            ? new Date(currentAlert.start_time).toISOString().slice(11, 19)
                                                            : '—')}
                                                </div>
                                            </div>

                                            <div className="inference-time-item">
                                                <strong>End:</strong>
                                                <div className="inference-value">
                                                    {currentAlert.type === "sensor"
                                                        ? (device?.end_time
                                                            ? new Date(device.end_time).toISOString().slice(11, 19)
                                                            : '—')
                                                        : (currentAlert.end_time
                                                            ? new Date(currentAlert.end_time).toISOString().slice(11, 19)
                                                            : '—')}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="inference-item" style={{ marginTop: '0.75rem' }}>
                                            <strong>LLM Response:</strong>
                                            <div className="inference-value">
                                                {currentAlert.llm_response || 'No LLM response available.'}
                                            </div>
                                        </div>
                                    </div>

                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default AlertDetailPage;