import React, { useState } from "react";
import "../AlertDeviceModal.css";
import { ENDPOINTS } from '../utils/appConfig';

function AlertDeviceModal({ alert, onClose }) {
    const [activeTab, setActiveTab] = useState(0);
    const devices = alert?.devices || [];

    const currentDevice = devices[activeTab];
    const isLive = alert.alert_analysis === "pending" || alert.alert_analysis === "failed";
    const Id="df96e4db-61a0-495b-b17c-177d32e27ecb";
    const videoSrc = ENDPOINTS.CAMERA_STREAM(Id)
                        

    return (
        <div className="device-modal-overlay" onClick={onClose}>
            <div className="device-modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header custom-modal-header-device">
                    <h5 className="modal-title w-100 text-center text-white m-0">Device Information</h5>
                    <button type="button" className="btn-close" aria-label="Close" onClick={onClose}></button>
                </div>
                <div className="alert-summary-block">
                    <div className="alert-id">Video Analysis – {alert.id}</div>
                    <div className="alert-description">{alert.message}</div>
                </div>

                {/* Tabs */}
                <div className="device-tabs" style={{ display: "grid", gridTemplateColumns: `repeat(${devices.length}, 1fr)`, gap: "0.5rem" }}>
                    {devices.map((device, index) => (
                        <button
                            key={index}
                            className={`tab-btn ${activeTab === index ? "active" : ""}`}
                            onClick={() => setActiveTab(index)}
                        >
                            {device.name}
                        </button>
                    ))}
                </div>
                <div className="device-modal-body">
                    <div className="video-section-device">
                        <video width="680" height="480" controls autoPlay src={videoSrc} />
                    </div>
                    <div className="info-section">
                        <div className="info-block">
                            <h5>Device Information</h5>
                            <p><strong>Device:</strong> {currentDevice.name}</p>
                            <p><strong>Type:</strong> {currentDevice.type}</p>
                            <p><strong>Angle:</strong> 68°</p>
                            <p><strong>Direction:</strong> West</p>
                            <p><strong>Duration:</strong> 5:00</p>
                        </div>

                        <div className="info-block">
                            <h5>Recording Timeline</h5>
                            <p><strong>Start:</strong> 08:14 AM</p>
                            <p><strong>End:</strong> 08:19 AM</p>
                        </div>

                        <div className="info-block">
                            <h5>Inference Analysis</h5>
                            <p><strong>Status:</strong> Failed</p>
                            <p><strong>Detection:</strong> Safety Violation</p>
                            <p><strong>Severity:</strong> Medium</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default AlertDeviceModal;