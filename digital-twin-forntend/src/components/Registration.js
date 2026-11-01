import React, { useEffect, useState } from "react";
import "../register.css";
import { fetchRoles, registerUser, UpdateUser } from "../utils/appClient";
import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { Eye, EyeOff } from "lucide-react";

function RegistrationPage({ isModal, onClose, reloadUserList, selectedUser }) {
  const [roles, setRoles] = useState([]);
  const [role, setRole] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [first_name, setFirstName] = useState("");
  const [last_name, setLastName] = useState("");
  const [is_staff, setIsStaff] = useState(false);
  const [isEdit, setIsEdit] = useState(false);
  const [id, setId] = useState("");
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);


  useEffect(() => {
    if (selectedUser && selectedUser.id) {
      setIsEdit(true);
      setId(selectedUser.id);
      setUsername(selectedUser.username || "");
      setEmail(selectedUser.email || "");
      setFirstName(selectedUser.first_name || "");
      setLastName(selectedUser.last_name || "");
      setRole(selectedUser.role ? String(selectedUser.role) : "");
      setIsStaff(selectedUser.is_staff || false);
    } else {
      setIsEdit(false);
      setId("");
      setUsername("");
      setEmail("");
      setPassword("");
      setFirstName("");
      setLastName("");
      setIsStaff(false);
      setRole(null);
    }
  }, [selectedUser]);

  useEffect(() => {
    const loadRoles = async () => {
      let roleData = await fetchRoles();
      roleData = roleData.map((r) => ({
        ...r,
        id: String(r.id),
        name: r.name.charAt(0).toUpperCase() + r.name.slice(1),
      }));
      roleData.sort((a, b) => a.name.localeCompare(b.name));
      setRoles(roleData);


    };

    loadRoles();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newErrors = {};


    if (!username.trim()) {
      newErrors.username = "Username is required.";
    } else if (username.length < 4 || username.length > 20) {
      newErrors.username = "Username must be between 4 and 20 characters long.";
    } else if (!/^[\w.@+-]+$/.test(username)) {
      newErrors.username = "Username can contain only letters, numbers, and @/./+/-/_";
    }


    if (!email.trim()) {
      newErrors.email = "Email is required.";
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = "Enter a valid email address.";
    }

    if (!isEdit && !password.trim()) {
      newErrors.password = "Password is required.";
    } else if (password && password.length < 8) {
      newErrors.password = "Password must be at least 8 characters long.";
    } else if (password && password.length > 24) {
      newErrors.password = "Password must be at most 24 characters long";
    }

    if (!role) newErrors.role = "Please select a role.";

    setErrors(newErrors);

    if (Object.keys(newErrors).length > 0) {
      toast.error("Please fix the highlighted errors.");
      return;
    }

    const payload = { id, username, email, first_name, last_name, role, is_staff };
    if (!isEdit || (isEdit && password.trim() !== "")) payload.password = password;

    try {
      let response = isEdit ? await UpdateUser(payload) : await registerUser(payload);
      const responseData = await response.json().catch(() => null);

      if (!response.ok) {
        if (response.status === 400 && responseData && typeof responseData === "object") {
          const backendErrors = {};
          for (const [key, value] of Object.entries(responseData)) {
            backendErrors[key] = Array.isArray(value) ? value.join(", ") : value;
          }
          setErrors(backendErrors);
          toast.error("Please fix the highlighted errors.");
        } else {
          const errorMsg = responseData?.detail || responseData?.error || "An unexpected error occurred.";
          toast.error(errorMsg);
        }
        if (response.status === 500) toast.error("Something went wrong on the server. Please try again later.");
        return;
      }

      toast.success(isEdit ? "User updated successfully!" : "User registered successfully!");
      if (onClose) onClose();
      if (reloadUserList) reloadUserList();
    } catch (error) {
      console.error("Submission failed:", error);
      toast.error("An error occurred while submitting the form.");
    }
  };

  return (
    <div className={isModal ? "modal-form-wrapper" : "register-wrapper"}>
      <form className="form-container border shadow-sm" onSubmit={handleSubmit}>

        <div className="form-group mb-3">
          <label htmlFor="InputFirstName">First Name</label>
          <input
            type="text"
            className="form-control"
            id="InputFirstName"
            placeholder="Enter First Name"
            value={first_name}
            onChange={(e) => setFirstName(e.target.value)}
          />
          {errors.first_name && <div className="invalid-feedback">{errors.first_name}</div>}
        </div>

        <div className="form-group mb-3">
          <label htmlFor="InputLastName">Last Name</label>
          <input
            type="text"
            className="form-control"
            id="InputLastName"
            placeholder="Enter Last Name"
            value={last_name}
            onChange={(e) => setLastName(e.target.value)}
          />
          {errors.last_name && <div className="invalid-feedback">{errors.last_name}</div>}
        </div>


        <div className="form-group mb-3">
          <label htmlFor="InputUsername">
            User Name {!isEdit && <span className="text-danger">*</span>}
          </label>
          <input
            type="text"
            className={`form-control ${errors.username ? "is-invalid" : ""}`}
            id="InputUsername"
            placeholder="Enter User Name"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <small
            className={`form-text ${errors.username &&
                errors.username !== "Username is required."
                ? "text-danger"
                : "text-muted"
              }`}
          >
            Must be 4–20 characters. Letters, numbers, and @/./+/-/_ only.
          </small>


          {errors.username === "Username is required." && (
            <div className="invalid-feedback d-block">{errors.username}</div>
          )}
        </div>



        <div className="form-group mb-3">
          <label htmlFor="InputEmail">
            Email {!isEdit && <span className="text-danger">*</span>}
          </label>
          <input
            type="email"
            className={`form-control ${errors.email ? "is-invalid" : ""}`}
            id="InputEmail"
            placeholder="Enter Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          {(errors.email || !email.trim()) && (
            <div className="invalid-feedback">
              {!email.trim() ? "Email is required." : errors.email}
            </div>
          )}
        </div>


        <div className="form-group mb-3 position-relative">
          <label htmlFor="InputPassword">
            Password {!isEdit && <span className="text-danger">*</span>}
          </label>
          <div className="input-group">
            <input
              type={showPassword ? "text" : "password"}
              className={`form-control ${errors.password ? "is-invalid" : ""}`}
              id="InputPassword"
              placeholder={isEdit ? "Enter New Password" : "Enter Password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={() => setShowPassword(!showPassword)}
              style={{ borderTopLeftRadius: 0, borderBottomLeftRadius: 0 }}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>


          <small
            className={`form-text ${errors.password &&
                errors.password !== "Password is required."
                ? "text-danger"
                : "text-muted"
              }`}
          >
            Must be 8–24 characters. Can't be entirely numeric.
          </small>


          {errors.password === "Password is required." && (
            <div className="invalid-feedback d-block">{errors.password}</div>
          )}
        </div>



        <div className="form-group mb-3">
          <label htmlFor="InputStaff">Staff</label>
          <select
            className="form-control"
            id="InputStaff"
            value={is_staff ? "true" : "false"}
            onChange={(e) => setIsStaff(e.target.value === "true")}
          >
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
          <small className="form-text text-muted">
            Select “Yes” if this user has staff privileges.
          </small>
        </div>


        <div className="form-group mb-3">
          <label htmlFor="InputRole">Role</label>
          <select
            className={`form-control ${errors.role ? "is-invalid" : ""}`}
            id="InputRole"
            value={role || ""}
            onChange={(e) => setRole(e.target.value)}
          >
            <option value="">Select Role</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
          {errors.role && <div className="invalid-feedback">{errors.role}</div>}

        </div>


        <button type="submit" className="btn btn-primary w-100">
          {isEdit ? "Update User" : "Register User"}
        </button>
      </form>
    </div>
  );
}

export default RegistrationPage;
