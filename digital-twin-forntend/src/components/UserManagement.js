import { useState, useEffect } from "react";
import "../UserManagement.css";
import { fetchAuthList, fetchRoles } from "../utils/appClient";
import AddUserModal from "../components/AddUserModal";
import Sidebar from "../components/SideBar";
import securityIcon from "../images/security-cameras.png";
import { hasRole, ROLES } from "../utils/Helpers";

function UserManagement() {
  const [userData, setUserData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const usersPerPage = 10;
  const [showLeftMenu, setShowLeftMenu] = useState(false);
  const username = localStorage.getItem("username");
  const [roles, setRoles] = useState({});

  const handleSignOut = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  const hasRoleFn = (allowedRoles) => {
    const role = localStorage.getItem("role");
    return allowedRoles.includes(ROLES.ALL) || allowedRoles.includes(role);
  };

  useEffect(() => {
    document.body.classList.toggle("modal-open", showModal);
    return () => document.body.classList.remove("modal-open");
  }, [showModal]);


  const fetchUserList = async () => {
    try {
      const data = await fetchAuthList();

      const sortedData = [...data].sort((a, b) =>
        a.username.toLowerCase().localeCompare(b.username.toLowerCase())
      );

      setUserData(sortedData);
    } catch (err) {
      console.error("Failed to fetch user list:", err);
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchUserList();
  }, []);

  useEffect(() => {
    const loadRoles = async () => {
      let roleData = await fetchRoles();
      const roleMap = {};
      roleData.forEach(r => {
        roleMap[r.id] = r.name.charAt(0).toUpperCase() + r.name.slice(1);
      });
      setRoles(roleMap);
    };
    loadRoles();
  }, []);

  function handleEdit(user) {
    setSelectedUser(user);
    setShowModal(true);
  }

  if (loading) return <p>Loading user details...</p>;
  if (!userData || userData.length === 0) return <p>No user data found.</p>;

  const indexOfLastUser = currentPage * usersPerPage;
  const indexOfFirstUser = indexOfLastUser - usersPerPage;
  const currentUsers = userData.slice(indexOfFirstUser, indexOfLastUser);
  const totalPages = Math.ceil(userData.length / usersPerPage);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
  };

  return (
    <>
      <div
        className="usermanage-wrapper"
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
              User Management
            </span>
          </div>

          <div
            className="user-page-container"
            style={{
              display: "flex",
              flexDirection: "column",
              minHeight: 0,
              flex: 1,
              overflow: "hidden",
              paddingTop: "50px",
            }}
          >
          <div className="user-list">
            <div className="user-list-headers">
              <h3 className="user-title">Manage Users</h3>
              {hasRole(ROLES.ADMIN_ONLY) && (
                <button className="useradd-btn" onClick={() => setShowModal(true)}>
                  Add User
                </button>
              )}
            </div>


            <div className="usermanage-table-wrapper">
              <table className="user-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>User Name</th>
                    <th>Email</th>
                    <th className="user-table-staff-role-col">Roles</th>
                    <th className="user-table-staff-status-col">Staff Status</th>
                    {hasRole(ROLES.ADMIN_ONLY) ? (
                      <th className="edit-cell">Edit</th>
                    ) : (
                      <th className="edit-cell"></th>
                    )}
                  </tr>
                </thead>

                <tbody>
                  {currentUsers.map((user) => (
                    <tr key={user.id}>
                      <td>
                        {user.first_name || user.last_name
                          ? `${user.first_name} ${user.last_name}`
                          : "N/A"}
                      </td>
                      <td>{user.username}</td>
                      <td>{user.email}</td>
                      <td className="user-table-staff-role-col">
                        {roles[user.role] || "NA"}
                      </td>
                      <td className="user-table-staff-status-col">
                        {user.is_staff ? "✅" : "❌"}
                      </td>
                      {hasRole(ROLES.ADMIN_ONLY) ? (
                        <td className="edit-cell">
                          <button className="edit-btn" onClick={() => handleEdit(user)}>🖋️</button>
                        </td>
                      ) : (
                        <td className="edit-cell"></td>
                      )}

                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="pagination">
                {Array.from({ length: totalPages }, (_, index) => (
                  <button
                    key={index + 1}
                    className={`page-btn ${currentPage === index + 1 ? "active" : ""}`}
                    onClick={() => handlePageChange(index + 1)}
                  >
                    {index + 1}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      </div>
      {showModal && (
        <AddUserModal
          onClose={() => {
            setShowModal(false);
            setSelectedUser({});
          }}
          reloadUserList={fetchUserList}
          selectedUser={selectedUser}
        />
      )}
    </>
  );
}

export default UserManagement;