import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import '../DeviceDetail.css';
import { formatFriendlyTimestamp } from '../utils/Helpers';
import { fetchDeviceDetail } from '../utils/appClient';
import { ROLES } from "../utils/Helpers";
import Sidebar from "../components/SideBar";
import securityIcon from "../images/security-cameras.png";

function DeviceDetail() {
  const { deviceId } = useParams();
  const [deviceData, setDeviceData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showLeftMenu, setShowLeftMenu] = useState(false);
  const username = localStorage.getItem("username");

  const handleSignOut = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  const hasRoleFn = (allowedRoles) => {
    const role = localStorage.getItem("role");
    return allowedRoles.includes(ROLES.ALL) || allowedRoles.includes(role);
  };

  useEffect(() => {
    async function loadDeviceDetail() {
      try {
        const response = await fetchDeviceDetail(deviceId);
        setDeviceData(response);
      } catch (err) {
        console.error('Failed to fetch device detail:', err);
      } finally {
        setLoading(false);
      }
    }
    loadDeviceDetail();
  }, [deviceId]);

  if (loading) return <p>Loading device details...</p>;
  if (!deviceData) return <p>No device data found.</p>;

  const renderCard = (item, type) => (
    <div key={`${type}-${item.id}`} className="device-vertical-card">
      <p><strong>Name:</strong> {item.name}</p>
      <p><strong>Type:</strong> {item.camera_type || type.toUpperCase()}</p>
      <p><strong>Installed:</strong> {item.installation_date ? formatFriendlyTimestamp(item.installation_date) : '—'}</p>
      <p><strong>Last Maintenance:</strong> {item.last_maintenance ? formatFriendlyTimestamp(item.last_maintenance) : 'Not Updated'}</p>
    </div>
  );

  return (
    <>
      <div
        className="device-wrapper"
        style={{
          display: "grid",
          gridTemplateColumns: showLeftMenu ? "240px 1fr" : "0px 1fr",
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
          collapsed={!showLeftMenu}
        />

        <div className="main-content" style={{ flexGrow: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div className="top-nav-bar d-flex align-items-center px-3 py-2 gap-2">
            <button
              className="btn btn-link text-white p-0 icon-only"
              onClick={() => setShowLeftMenu(prev => !prev)}
              title={showLeftMenu ? "Close Menu" : "Open Menu"}
              aria-label="Toggle Sidebar"
            >
              <img
                src={securityIcon}
                alt="Toggle Sidebar"
                className="sidebar-toggle-icon"
              />
            </button>
            <span className="text-white fw-semibold devicedetail-header-title">Device Detail</span>
          </div>

          <div
            className="alert-detail-container"
            style={{
              display: "flex",
              flexDirection: "column",
              minHeight: 0,
              flex: 1,
              overflow: "auto"
            }}
          >
          <div className="device-section">
            <h3>Cameras</h3>
            <div className="device-card-row">
              {deviceData.cameras.length > 0
                ? deviceData.cameras.map((cam) => renderCard(cam, 'camera'))
                : <p className="no-record">No camera records found.</p>}
            </div>

            <h3>Drones</h3>
            <div className="device-card-row">
              {deviceData.drones.length > 0
                ? deviceData.drones.map((drone) => renderCard(drone, 'drone'))
                : <p className="no-record">No drone records found.</p>}
            </div>

            <h3>Sensors</h3>
            <div className="device-card-row">
              {deviceData.sensors.length > 0
                ? deviceData.sensors.map((sensor) => renderCard(sensor, 'sensor'))
                : <p className="no-record">No sensor records found.</p>}
            </div>
          </div>
        </div>
      </div>
      </div>
    </>
  );
}

export default DeviceDetail;