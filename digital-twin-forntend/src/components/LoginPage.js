import React, { useState } from "react";
import { parseJwt } from "../utils/jwtDecoder";
import { loginUser } from '../utils/appClient';
import { useNavigate } from "react-router-dom";
import { FaEye, FaEyeSlash } from "react-icons/fa";
import "../login.css";

function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const navigate = useNavigate();

  const validate = () => {
    const newErrors = {};
    const usernameRegex = /^[a-zA-Z0-9_]{3,20}$/;
    if (!username.trim()) {
      newErrors.username = "Username is required";
    } else if (username.length < 3) {
      newErrors.username = "Username must be at least 3 characters";
    } else if (username.length > 20) {
      newErrors.username = "Username must be no more than 20 characters";
    }
    // else if (!usernameRegex.test(username)) {
    //   newErrors.username = "Invalid username: only letters, numbers, and underscores allowed";
    // }
    if (!password.trim()) {
      newErrors.password = "Password is required";
    } else if (password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    return newErrors;
  };
  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    try {
      const data = await loginUser(username, password);
      if (data) {
        localStorage.setItem('accessToken', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        localStorage.setItem("isAuthenticated", "true");
      }
      const decoded = parseJwt(data.access);
      if (decoded) {
        localStorage.setItem('username', decoded.username);
        localStorage.setItem('role', decoded.role);
        console.log('Logged in as:', decoded.username, 'Role:', decoded.role);
      }
  navigate("/alert-dashboard");
    } catch (error) {
      if (error.message === "No active account found with the given credentials.") {
        error.message = "Invalid Username or Password."
      }
      setErrors({ password: error.message });
    }
  };

  return (
    <div className="login-page">
      <div className="top-nav-bar-login"></div>
      <div className="login-wrapper">
        <form className="form-container-login border shadow-sm" onSubmit={handleSubmit}>
          <h4 className="text-center mb-4 fw-bold">Login</h4>

          <div className="form-group mb-3">
            <input
              type="text"
              className={`form-control ${errors.username ? "is-invalid" : ""}`}
              id="InputUsername"
              placeholder="Enter Username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            {errors.username && (
              <div className="invalid-feedback">{errors.username}</div>
            )}
          </div>

          <div className="form-group mb-4">
            <div className="position-relative">
              <input
                type={showPassword ? "text" : "password"}
                className={`form-control ${errors.password ? "is-invalid" : ""}`}
                id="InputPassword"
                placeholder="Enter Password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingRight: "40px" }}
              />
              <span
                className="password-toggle-icon"
                onClick={() => setShowPassword((prev) => !prev)}
                style={{
                  position: "absolute",
                  right: "30px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  cursor: "pointer",
                  color: "#888",
                  paddingBottom: "3px"
                }}
              >
                {showPassword ? <FaEyeSlash /> : <FaEye />}
              </span>
            </div>
            {errors.password && (
              <div className="invalid-feedback d-block">{errors.password}</div>
            )}
          </div>

          <div className="d-flex justify-content-center">
            <div className="w-66">
              <button type="submit" className="btn btn-primary w-100">
                Sign in
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;