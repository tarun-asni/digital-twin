import React from "react";
import "../AlertDeviceModalNew.css";
function AlertDeviceModal({ alert, onClose }) {
  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <h4>Device Details for Alert {alert.id}</h4>
        <p><strong>Location:</strong> {alert.location}</p>
        <p><strong>Description:</strong> {alert.message}</p>

        <table className="device-table">
          <thead>
            <tr>
              <th>Device Name</th>
              <th>Type</th>
              <th>Timestamp</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {alert.devices.map((device, index) => (
              <tr key={index}>
                <td>{device.camera?.name}</td>
                <td>{device.type}</td>
                <td>{new Date(device.recorded_at).toLocaleTimeString()}</td>
                <td>{device.status}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="modal-actions">
          <button className="btn-close" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default AlertDeviceModal;