import { useState, useEffect } from "react";
import "../DeviceSettings.css";
import { useParams, useLocation } from "react-router-dom";
import { ENDPOINTS } from "../utils/appConfig";
import { fetchDeviceConfiguration, refreshAccessToken } from '../utils/appClient';
import Sidebar from "../components/SideBar";
import securityIcon from "../images/security-cameras.png";
import { hasRole, ROLES } from "../utils/Helpers";

function DeviceSettings() {
  const { deviceId } = useParams();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const deviceName = queryParams.get("name") || "";
  const [showLeftMenu, setShowLeftMenu] = useState(false);
  const username = localStorage.getItem("username");
  const convertISTtoUTCTimeOnly = (timeStr) => {
    const [hours, minutes, seconds = "00"] = timeStr.split(":").map(Number);
    let totalMinutes = hours * 60 + minutes;
    totalMinutes -= 330;
    if (totalMinutes < 0) totalMinutes += 24 * 60;
    if (totalMinutes >= 24 * 60) totalMinutes -= 24 * 60;

    const utcHours = Math.floor(totalMinutes / 60);
    const utcMinutes = totalMinutes % 60;

    return `${String(utcHours).padStart(2, "0")}:${String(utcMinutes).padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  };
  const handleSignOut = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  const hasRoleFn = (allowedRoles) => {
    const role = localStorage.getItem("role");
    return allowedRoles.includes(ROLES.ALL) || allowedRoles.includes(role);
  };

  const [deviceData, setDeviceData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ start_time: "", end_time: "", status: "" });
  const [editingId, setEditingId] = useState(null);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    async function loadDeviceConfig() {
      try {
        const response = await fetchDeviceConfiguration(deviceId);
        setDeviceData(response);
      } catch (err) {
        console.error("Failed to fetch device detail:", err);
      } finally {
        setLoading(false);
      }
    }
    loadDeviceConfig();
  }, [deviceId, reload]);

  if (loading) return <p>Loading device details...</p>;
  if (!deviceData) return <p>No device data found.</p>;

  const timeRegex = /^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$/;

  const isPartialTimeValid = (value) => {
    const parts = value.split(":");
    if (parts.length > 3) return false;
    if (parts[0] && (!/^\d{0,2}$/.test(parts[0]) || parseInt(parts[0]) > 23)) return false;
    if (parts[1] && (!/^\d{0,2}$/.test(parts[1]) || parseInt(parts[1]) > 59)) return false;
    if (parts[2] && (!/^\d{0,2}$/.test(parts[2]) || parseInt(parts[2]) > 59)) return false;
    return true;
  };

  const handleInputChange = (e) => {
    const { id, value } = e.target;
    setFormData((prev) => ({ ...prev, [id]: value }));

    if (id === "start_time" || id === "end_time") {
      if (!isPartialTimeValid(value)) {
        setErrors((prev) => ({ ...prev, [id]: "Invalid time format (HH:MM:SS)." }));
      } else {
        setErrors((prev) => {
          const { [id]: removed, ...rest } = prev;
          return rest;
        });
      }

      if (
        id === "end_time" &&
        timeRegex.test(formData.start_time) &&
        timeRegex.test(value)
      ) {
        if (formData.start_time >= value) {
          setErrors((prev) => ({ ...prev, end_time: "End Time must be greater than Start Time." }));
        } else {
          setErrors((prev) => {
            const { end_time, ...rest } = prev;
            return rest;
          });
        }
      }
    }
  };

  const resetForm = () => {
    setFormData({ start_time: "", end_time: "", status: "" });
    setEditingId(null);
    setErrors({});
    setShowModal(false);
  };

  const validateForm = () => {
    const newErrors = {};
    if (!formData.start_time) newErrors.start_time = "Start Time is required.";
    else if (!timeRegex.test(formData.start_time)) newErrors.start_time = "Invalid time format (HH:MM:SS).";
    if (!formData.end_time) newErrors.end_time = "End Time is required.";
    else if (!timeRegex.test(formData.end_time)) newErrors.end_time = "Invalid time format (HH:MM:SS).";
    if (
      timeRegex.test(formData.start_time) &&
      timeRegex.test(formData.end_time) &&
      formData.start_time >= formData.end_time
    ) {
      newErrors.end_time = "End Time must be greater than Start Time.";
    }
    if (!formData.status) newErrors.status = "Please select a Status.";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  let accessToken = localStorage.getItem('accessToken');

  const payload = {
    ...formData,
    device: deviceId
  };

  const handleAdd = async () => {
    if (!validateForm()) return;
    let accessToken = localStorage.getItem('accessToken');
    const payload = {
      ...formData,
      device: deviceId,
      start_time: convertISTtoUTCTimeOnly(formData.start_time),
      end_time: convertISTtoUTCTimeOnly(formData.end_time),
    };

    const makeRequest = async (token) => {
      return await fetch(ENDPOINTS.DEVICE_CONFIG_POST, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
    };
    try {
      let response = await makeRequest(accessToken);
      if (response.status === 401 || response.status === 403) {
        accessToken = await refreshAccessToken();
        response = await makeRequest(accessToken);
      }
      if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
      resetForm();
      setReload((prev) => !prev);
    } catch (error) {
      console.error('Error while adding configuration:', error);
      alert("Error while adding configuration");
    }
  };

  const handleSave = async () => {
    if (!validateForm() || editingId === null) return;
    const payload = {
      ...formData,
      device: deviceId,
      start_time: convertISTtoUTCTimeOnly(formData.start_time),
      end_time: convertISTtoUTCTimeOnly(formData.end_time),
    };

    try {
      let accessToken = localStorage.getItem("accessToken");
      let response = await fetch(ENDPOINTS.DEVICE_CONFIG_PUT(payload.id), {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.status === 401 || response.status === 403) {
        accessToken = await refreshAccessToken();
        response = await fetch(ENDPOINTS.DEVICE_CONFIG_PUT(payload.id), {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });
      }

      if (!response.ok)
        throw new Error(`Error ${response.status}: ${response.statusText}`);

      const updatedConfig = await response.json();
      setDeviceData((prev) =>
        prev.map((device) =>
          device.id === editingId ? updatedConfig : device
        )
      );
      resetForm();
    } catch (error) {
      console.error("Error while saving configuration:", error);
      alert("Error while saving configuration");
    }
  };

  const handleCancel = () => resetForm();
  const handleEdit = (device) => {
    setFormData({ id: device.id, start_time: device.start_time, end_time: device.end_time, status: device.status });
    setEditingId(device.id);
    setShowModal(true);
  };

  const isEditMode = editingId !== null;
  const formatDateTime = (isoString) => {
    const date = new Date(isoString);
    const dd = String(date.getDate()).padStart(2, '0');
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const yyyy = date.getFullYear();
    let hh = date.getHours();
    const min = String(date.getMinutes()).padStart(2, '0');
    const ss = String(date.getSeconds()).padStart(2, '0');
    const ampm = hh >= 12 ? 'PM' : 'AM';
    hh = hh % 12 || 12;
    return `${dd}-${mm}-${yyyy} ${String(hh).padStart(2, '0')}:${min}:${ss} ${ampm}`;
  };

  return (
    <>
      <div
        className="config-wrapper"
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
            <span className="text-white fw-semibold devicesetting-header-title">Configuration</span>
          </div>

          <div
            className="page-container"
            style={{
              display: "flex",
              flexDirection: "column",
              minHeight: 0,
              flex: 1,
              overflowY: "auto"
            }}
          >
            <div className="device-list">
              <div className="device-list-headers">
                <h3 className="title">Configuration for {deviceName}</h3>
                {!isEditMode && (
                  <button className="add-btn" onClick={() => setShowModal(true)}>
                    Add
                  </button>
                )}
              </div>

              <div className="table-wrapper">
                <table className="device-table">
                  <thead>
                    <tr>
                      <th>Start Time</th>
                      <th>End Time</th>
                      <th>Status</th>
                      <th>Created At</th>
                      <th>Updated At</th>
                      <th>Edit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deviceData.map((device, index) => (
                      <tr key={device.id} className={index % 2 === 0 ? "" : "row-alt"}>
                        <td>{device.start_time}</td>
                        <td>{device.end_time}</td>
                        <td>
                          <span className={`status ${device.status.toLowerCase()}`}>
                            {device.status}
                          </span>
                        </td>
                        <td>{formatDateTime(device.created_at)}</td>
                        <td>{formatDateTime(device.updated_at)}</td>
                        <td>
                          <button className="edit-btn" onClick={() => handleEdit(device)}>
                            🖋️
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {showModal && (
              <div className="modal-overlay-form">
                <div className="modal-content-form">
                  <h3>{isEditMode ? "Edit Configuration" : "Add New Configuration"}</h3>

                  <div className="form-group">
                    <label>Device Name <span className="mandatory">*</span></label>
                    <div className="static-text">{deviceName}</div>
                  </div>

                  <div className="form-group">
                    <label htmlFor="start_time">Start Time <span className="mandatory">*</span></label>
                    <input
                      id="start_time"
                      value={formData.start_time}
                      onChange={handleInputChange}
                      placeholder="HH:MM:SS"
                    />
                    {errors.start_time && <div className="error">{errors.start_time}</div>}
                  </div>

                  <div className="form-group">
                    <label htmlFor="end_time">End Time <span className="mandatory">*</span></label>
                    <input
                      id="end_time"
                      value={formData.end_time}
                      onChange={handleInputChange}
                      placeholder="HH:MM:SS"
                    />
                    {errors.end_time && <div className="error">{errors.end_time}</div>}
                  </div>

                  <div className="form-group">
                    <label htmlFor="status">Status <span className="mandatory">*</span></label>
                    <select id="status" value={formData.status} onChange={handleInputChange}>
                      <option value="">Select Status</option>
                      <option value="enabled">Enabled</option>
                      <option value="disabled">Disabled</option>
                    </select>
                    {errors.status && <div className="error">{errors.status}</div>}
                  </div>

                  <div className="btn-group">
                    {!isEditMode && <button className="btn add" onClick={handleAdd}>Add</button>}
                    {isEditMode && (
                      <>
                        <button className="btn save" onClick={handleSave}>Save</button>
                        <button className="btn cancel" onClick={handleCancel}>Cancel</button>
                      </>
                    )}
                    <button className="btn cancel" onClick={handleCancel}>Close</button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export default DeviceSettings;
