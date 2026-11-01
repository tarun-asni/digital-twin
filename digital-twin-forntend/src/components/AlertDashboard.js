import React, { useState, useEffect } from "react";
import Sidebar from "../components/SideBar";
import AlertDeviceModal from "./AlertDeviceModal";
import ActiveAlertsView from "./ActiveAlertsView";
import AllAlertsView from "./AllAlertsView";
import { hasRole, ROLES } from "../utils/Helpers";
import securityIcon from "../images/security-cameras.png";
import "../AlertDashboard.css";
import { fetchAlertsList, fetchSensorAlerts } from '..//utils/appClient';
import dummyAlerts from "../data/dummyAlerts";
function AlertDashboard() {
  const [alerts, setAlerts] = useState([]);
  const [filteredAlerts, setFilteredAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const [activeTab, setActiveTab] = useState("active");
  const [showLeftMenu, setShowLeftMenu] = useState(false);
  const username = localStorage.getItem("username");

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [expandedAlertId, setExpandedAlertId] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showDeviceModal, setShowDeviceModal] = useState(false);

  const handleSignOut = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  const hasRoleFn = (allowedRoles) => {
    const role = localStorage.getItem("role");
    return allowedRoles.includes(ROLES.ALL) || allowedRoles.includes(role);
  };

  useEffect(() => {
    if (activeTab === "active") {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    async function loadAlerts() {
      try {
        const [cameraData, sensorData] = await Promise.all([
          fetchAlertsList(),
          fetchSensorAlerts()
        ]);
        const normalizedSensorAlerts = sensorData.map(sensor => ({
          id: sensor.sensor_alert,
          type: "sensor",
          sensor_id: sensor.sensor_id,
          drone_id: sensor.drone_id,
          drone_flight_id: sensor.drone_flight_id,
          message: sensor.description,
          start_time: sensor.timestamp,
          alert_analysis: sensor.status,
          title: sensor.description || "Sensor Alert",
          severity: sensor.severity,
          drone: {
            id: sensor?.drone?.id,
            name: sensor?.drone?.name,
            model: sensor?.drone?.model,
            manufacturer: sensor?.drone?.manufacturer,
            serial_number: sensor?.drone?.serial_number,
            latitude: sensor?.drone?.latitude,
            longitude: sensor?.drone?.longitude,
            altitude: sensor?.drone?.altitude,
            is_active: sensor?.drone?.is_active,
            installation_date: sensor?.drone?.installation_date,
            last_maintenance: sensor?.drone?.last_maintenance,
            notes: sensor?.drone?.notes,
            drone_type: sensor?.drone?.drone_type,
            is_in_flight: sensor?.drone?.is_in_flight,
            battery_percentage: sensor?.drone?.battery_percentage,
            camera_specs: sensor?.drone?.camera_specs,
            gps_enabled: sensor?.drone?.gps_enabled,
            obstacle_avoidance: sensor?.drone?.obstacle_avoidance,
            autonomous_flight: sensor?.drone?.autonomous_flight,
            weather_resistance: sensor?.drone?.weather_resistance,
            edge_url: sensor?.drone?.edge_url,
          },
          devices: (sensor?.devices || []).map(device => ({
            id: device?.device_id,
            device_name: device?.device_name,
            primary: device?.primary_device,
            status: device?.status,
            recording_start: device?.recording_start,
            recording_end: device?.recording_end,
            video_url: device?.video_url,
          }))
        }));

        const combined = [...cameraData, ...normalizedSensorAlerts];

        setAlerts(cameraData);
        setFilteredAlerts(combined);
      } catch (error) {
        console.error("Error loading alerts:", error);
        setAlerts([]);
        setFilteredAlerts([]);
      } finally {
        setLoading(false);
      }
    }

    loadAlerts();
  }, []);

  return (
    <div
      className="alert-wrapper"
      style={{
        display: "grid",
        gridTemplateColumns: showLeftMenu ? "240px 1fr" : "0px 1fr",
        transition: "grid-template-columns 0.3s ease",
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
            <img src={securityIcon} alt="Toggle Sidebar" className="sidebar-toggle-icon" />
          </button>
          <span className="text-white fw-semibold user-header-title">Alert Monitoring Dashboard</span>
        </div>
        <div className="alert-page-container flex-grow-1 overflow-auto px-4 py-3">
          <div className="alert-content-wrapper">
            <div className="tab-bar">
              <button
                className={`tab-pill ${activeTab === "active" ? "active" : ""}`}
                onClick={() => setActiveTab("active")}
              >
                Active Alerts
              </button>
              <button
                className={`tab-pill ${activeTab === "all" ? "active" : ""}`}
                onClick={() => setActiveTab("all")}
              >
                All Alerts ({filteredAlerts.length})
              </button>
            </div>

            <div className="alert-view">
              {activeTab === "active" ? (
                <ActiveAlertsView
                  alerts={alerts}
                  setAlerts={setAlerts}
                  expandedAlertId={expandedAlertId}
                  setExpandedAlertId={setExpandedAlertId}
                  setSelectedAlert={setSelectedAlert}
                  setShowDeviceModal={setShowDeviceModal}
                />
              ) : (
                <AllAlertsView
                  alerts={filteredAlerts}
                  loading={loading}
                  searchTerm={searchTerm}
                  startDate={startDate}
                  endDate={endDate}
                  statusFilter={statusFilter}
                  setSearchTerm={setSearchTerm}
                  setStartDate={setStartDate}
                  setEndDate={setEndDate}
                  setStatusFilter={setStatusFilter}
                  expandedAlertId={expandedAlertId}
                  setExpandedAlertId={setExpandedAlertId}
                  setSelectedAlert={setSelectedAlert}
                  setShowDeviceModal={setShowDeviceModal}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {showDeviceModal && (
        <AlertDeviceModal alert={selectedAlert} onClose={() => setShowDeviceModal(false)} />
      )}
    </div>
  );
}

export default AlertDashboard;