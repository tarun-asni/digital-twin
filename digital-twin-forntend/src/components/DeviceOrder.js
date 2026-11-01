import React, { useState } from 'react';
import '../DeviceOrder.css';
import { submitDeviceOrder } from '../utils/appClient';
import Sidebar from "../components/SideBar";
import securityIcon from "../images/security-cameras.png";
import { hasRole, ROLES } from "../utils/Helpers";

function DeviceOrder() {
    const [name, setName] = useState('');
    const [type, setType] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
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

    const handleNameChange = (e) => {
        const input = e.target.value;
        if (/^[a-zA-Z0-9 ]*$/.test(input)) {
            setName(input);
            setError('');
        } else {
            setError('Device Name can only contain letters, numbers, and spaces.');
        }
    };

    const handleSubmit = async () => {
        const trimmedName = name.trim();
        const trimmedType = type.trim();

        if (!trimmedName || !trimmedType) {
            setError('Both fields are required.');
            return;
        }

        setError('');
        setLoading(true);
        const result = await submitDeviceOrder(trimmedName, trimmedType);

        setLoading(false);
        if (!result.success) {
            setError(result.error);
        } else {
            setName('');
            setType('');
        }
    };

    return (
        <>
            <div
                className="device-wrapper"
                style={{
                    display: "grid",
                    gridTemplateColumns: showLeftMenu ? "240px 1fr" : "0px 1fr",
                    transition: "grid-template-columns 0.3s ease",
                    height: "100vh",
                    overflow: "hidden"
                }}>
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
                            data-bs-toggle="tooltip"
                            data-bs-placement="bottom"
                            title={showLeftMenu ? "Close Menu" : "Open Menu"}
                            aria-label="Toggle Sidebar"
                        >
                            <img
                                src={securityIcon}
                                alt="Toggle Sidebar"
                                className="sidebar-toggle-icon"
                            />
                        </button>
                        <span className="text-white fw-semibold device-header-title">Device Order</span>
                    </div>

                    {loading && (
                        <div className="device-order-loading">
                            <div className="device-order-spinner"></div>
                            <p>Processing your request...</p>
                        </div>
                    )}

                    <div className="device-order-container">
                        {error && (
                            <div className="device-order-error">
                                {error}
                            </div>
                        )}

                        <div className="device-order-row">
                            <label className="device-order-label">Device Name:</label>
                            <input
                                type="text"
                                className="device-order-input"
                                value={name}
                                onChange={handleNameChange}
                            />
                        </div>

                        <div className="device-order-row">
                            <label className="device-order-label">Device Type:</label>
                            <select
                                className="device-order-input"
                                value={type}
                                onChange={(e) => setType(e.target.value)}
                            >
                                <option value="">Select Device Type</option>
                                <option value="SecurityCamera">SecurityCamera</option>
                                <option value="Drone">Drone</option>
                                <option value="Sensor">Sensor</option>
                                <option value="Camera">Camera</option>
                            </select>
                        </div>

                        <button
                            className="device-order-button"
                            onClick={handleSubmit}
                            disabled={!name.trim() || !type.trim()}
                            style={{
                                opacity: !name.trim() || !type.trim() ? 0.6 : 1,
                                cursor: !name.trim() || !type.trim() ? 'not-allowed' : 'pointer',
                            }}
                        >
                            📥 Submit
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}

export default DeviceOrder;