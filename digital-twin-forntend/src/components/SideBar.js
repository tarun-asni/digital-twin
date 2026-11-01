import React from "react";
import dashboardIcon from "../images/dashboard.svg";
import { ROLES } from "../utils/Helpers";

function Sidebar({
    username = "Guest",
    handleSignOut = () => {},
    hasRole = () => true,
    title = "",
    collapsed = false,
    style = {}
}) {

    const navItems = [
        { label: "🏠 Dashboard", path: "/alert-dashboard", roles: [ROLES.ALL] },
        { label: "🎙️ Voice Prompt", path: "/voice-prompt", roles: [ROLES.ALL] },
        { label: "📦 Device Order", path: "/device-order", roles: [ROLES.ADMIN_ONLY] },
        { label: "🖥️ Device List", path: "/device-list", roles: [ROLES.ALL] },
        { label: "👥 User Management", path: "/user-management", roles: [ROLES.ALL] },
        { label: "🧑‍💼 Role Management", path: "/role-management", roles: [ROLES.ADMIN_ONLY] },
    ];

    return (  
        <div className={`left-sidebar ${collapsed ? 'collapsed' : ''}`} style={style}>
            <div className="sidebar-user-info">
                <div className="sidebar-label">
                    <span className="user-icon">👤</span>
                    <span className="user-name">{username}</span>
                </div>
                <button onClick={handleSignOut}>
                    <i className="bi bi-box-arrow-right"></i>
                </button>
            </div>



            <ul className="nav flex-column gap-2">
                {navItems.map(({ label, path, roles }) =>
                    roles.some((role) => hasRole(role)) ? (
                        <li className="nav-item" key={path} onClick={() => window.open(path, "_blank")}>
                            <span className="sidebar-label">{label}</span>
                        </li>

                    ) : null
                )}
            </ul>
        </div>
    );
}

export default Sidebar;