import React, { useEffect, useState } from "react";
import "../AlertDetail.css";
import { fetchDeviceList } from "../utils/appClient";
import { formatFriendlyTimestamp } from "../utils/Helpers";
import { hasRole, ROLES } from "../utils/Helpers";
import Sidebar from "../components/SideBar";
import securityIcon from "../images/security-cameras.png";

function DeviceList() {
    const [devices, setDevices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sortOrder, setSortOrder] = useState("desc");
    const [showLeftMenu, setShowLeftMenu] = useState(false);
    const username = localStorage.getItem("username");
    const showSettings = hasRole(ROLES.ADMIN_ONLY);

    const handleSignOut = () => {
        localStorage.clear();
        window.location.href = "/login";
    };

    const hasRoleFn = (allowedRoles) => {
        const role = localStorage.getItem("role");
        return allowedRoles.includes(ROLES.ALL) || allowedRoles.includes(role);
    };

    useEffect(() => {
        async function loadDevices() {
            try {
                const data = await fetchDeviceList();
                const sorted = sortByUpdatedAt(data, "desc");
                setDevices(sorted);
            } catch (err) {
                console.error("Failed to load devices:", err);
            } finally {
                setLoading(false);
            }
        }
        loadDevices();
    }, []);

    const sortByUpdatedAt = (list, order) => {
        return [...list].sort((a, b) => {
            const timeA = new Date(a.updated_at).getTime();
            const timeB = new Date(b.updated_at).getTime();
            return order === "asc" ? timeA - timeB : timeB - timeA;
        });
    };

    const toggleSortOrder = () => {
        const newOrder = sortOrder === "asc" ? "desc" : "asc";
        setSortOrder(newOrder);
        setDevices(sortByUpdatedAt(devices, newOrder));
    };

    if (loading) return <p>Loading device list...</p>;
    if (!devices || devices.length === 0) return <p>No devices found.</p>;

    return (
        <>
            <div
                className="device-wrapper"
                style={{
                    display: "grid",
                    gridTemplateColumns: showLeftMenu ? "240px 1fr" : "0px 1fr",
                    gridTemplateRows: "auto 1fr",
                    overflow: "hidden"
                }}>
                <Sidebar
                    username={username}
                    handleSignOut={handleSignOut}
                    hasRole={hasRoleFn}
                    title=""
                    collapsed={!showLeftMenu}
                    style={{ gridRow: "1 / span 2", gridColumn: "1" }}
                />

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
                    <span className="text-white fw-semibold devicelist-header-title">Device List</span>
                </div>
                <div className="alert-detail-container" style={{ overflowY: "auto" }}>
                    <table className={`devicelist-table ${!showSettings ? "no-settings" : ""}`}>
                        <thead>
                            <tr>
                                <th className="device-name-col">Name</th>
                                <th className="device-type-col">Type</th>
                                <th className="device-status-col">Status</th>
                                <th className="device-updated-col" onClick={toggleSortOrder} style={{ cursor: 'pointer' }}>
                                    Last Updated {sortOrder === "asc" ? "↑" : "↓"}
                                </th>
                                {hasRole(ROLES.ADMIN_ONLY) ? (
                                    <th className="device-settings-col">Settings</th>
                                ) : (
                                    <th className="device-settings-col"></th>
                                )}
                            </tr>
                        </thead>
                        <tbody>
                            {devices.map((device) => (
                                <tr key={device.id}>
                                    <td className="device-name-col">
                                        <span
                                            className="device-link"
                                            onClick={() => window.open(`/device/${device.id}`, "_self", 'noopener,noreferrer')}
                                            style={{ cursor: 'pointer', color: '#0078d4', textDecoration: 'underline' }}
                                        >
                                            {device.name}
                                        </span>
                                    </td>
                                    <td className="device-type-col">{device.type}</td>
                                    <td className="device-status-col">
                                        <span className={device.status === 'ACTIVE' ? 'status-active' : 'status-inactive'}>
                                            {device.status}
                                        </span>
                                    </td>
                                    <td className="device-updated-col">{formatFriendlyTimestamp(device.updated_at)}</td>
                                    {hasRole(ROLES.ADMIN_ONLY) && (
                                        <td className="device-settings-col">
                                            {device.status === "ACTIVE" && (
                                                <button
                                                    onClick={() =>
                                                        window.open(
                                                            `/device/configuration/${device.id}?name=${encodeURIComponent(device.name)}`,
                                                            "_self",
                                                            "noopener,noreferrer"
                                                        )
                                                    }
                                                    id="settingheader"
                                                >
                                                    ⚙️
                                                </button>
                                            )}
                                        </td>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </>
    );
}

export default DeviceList;
