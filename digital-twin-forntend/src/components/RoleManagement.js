import { useState, useEffect } from "react";
import "../RoleManagement.css";
import { fetchRoles } from "../utils/appClient";
import Sidebar from "../components/SideBar";
import securityIcon from "../images/security-cameras.png";
import { hasRole, ROLES } from "../utils/Helpers";

function RoleManagement() {
  const [deviceData, setDeviceData] = useState([]);
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
    async function loadRoles() {
      try {
        const data = await fetchRoles();
        setDeviceData(data);
      } catch (err) {
        console.error("Failed to fetch users detail:", err);
      } finally {
        setLoading(false);
      }
    }
    loadRoles();
  }, []);

  if (loading) return <p>Loading role details...</p>;
  if (!deviceData || deviceData.length === 0) return <p>No user data found.</p>;

  return (
    <>
      <div
        className="role-wrapper"
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
            <span className="text-white fw-semibold user-header-title">
              Role Management
            </span>
          </div>

          <div
            className="role-page-container"
            style={{
              display: "flex",
              flexDirection: "column",
              minHeight: 0,
              flex: 1,
              overflow: "hidden"
            }}
          >
          <div className="role-list">
            <div className="role-list-headers d-flex justify-content-between align-items-center px-3 py-2">
            </div>
            <div className="table-wrapper">
              <table className="role-table">
                <thead>
                  <tr>
                    <th>Id</th>
                    <th>Role</th>
                    <th>Permissions</th>
                  </tr>
                </thead>
                <tbody>
                  {deviceData.map((role) => (
                    <tr key={role.id}>
                      <td>{role.id}</td>
                      <td>{role.name.charAt(0).toUpperCase() + role.name.slice(1)}</td>
                      <td>
                        {role.permissions && role.permissions.length > 0
                          ? role.permissions
                            .map((p) =>
                              p === 1
                                ? "Full Access"
                                : p === 2
                                  ? "View Access"
                                  : "Unknown"
                            )
                            .join(", ")
                          : "No permissions"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
          </div>
      </div>
    </>
  );
}

export default RoleManagement;
