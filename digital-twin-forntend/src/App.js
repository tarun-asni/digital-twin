import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import CameraDetail from './components/CameraDetail';
import AlertDetail from './components/AlertDetail'
import VoicePrompt from './components/VoicePrompts';
import DeviceList from './components/DeviceList';
import DeviceDetail from './components/DeviceDetail';
import DeviceOrder from './components/DeviceOrder';
import LoginPage from './components/LoginPage';
import Registration from './components/Registration'
import UserManagement from './components/UserManagement'
import DeviceConfig from './components/DeviceSettings';
import { ToastContainer } from 'react-toastify';
import RoleManagement from './components/RoleManagement';
import { ProtectedRoute } from "./utils/Helpers";
import AlertDashboard from './components/AlertDashboard';
import AlertDetailWrapper from "./components/AlertDetailWrapper";


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/registration" element={<Registration />} />
        <Route
          path="/alert-dashboard"
          element={
            <ProtectedRoute>
              {" "}
              <AlertDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/camera/:id"
          element={
            <ProtectedRoute>
              <CameraDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/alerts/:alertId"
          element={
            <ProtectedRoute>
              <AlertDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/voice-prompt"
          element={
            <ProtectedRoute>
              <VoicePrompt />{" "}
            </ProtectedRoute>
          }
        />
        <Route
          path="/device-list"
          element={
            <ProtectedRoute>
              <DeviceList />
            </ProtectedRoute>
          }
        />
        <Route
          path="/device/:deviceId"
          element={
            <ProtectedRoute>
              <DeviceDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/device-order"
          element={
            <ProtectedRoute>
              <DeviceOrder />
            </ProtectedRoute>
          }
        />
        <Route
          path="/device/configuration/:deviceId"
          element={
            <ProtectedRoute>
              <DeviceConfig />
            </ProtectedRoute>
          }
        />
        <Route
          path="/user-management"
          element={
            <ProtectedRoute>
              <UserManagement />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/camera/:id" element={<CameraDetail />} />
        <Route path="/alerts/:alertId" element={<AlertDetail />} />
        <Route path="/voice-prompt" element={<VoicePrompt />} />
        <Route path="/device-list" element={<DeviceList />} />
        <Route path="/device/:deviceId" element={<DeviceDetail />} />
        <Route path="/device-order" element={<DeviceOrder />} />
        <Route path="/device/configuration/:deviceId" element={<DeviceConfig />} />
        <Route path="/user-management" element={<UserManagement />} />
        <Route path="/role-management" element={<RoleManagement />} />
        <Route path="/alert-details" element={<AlertDetailWrapper />} />
        <Route path="/alert-dashboard" element={<AlertDashboard />} />

      </Routes>
      <ToastContainer
        position="bottom-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        pauseOnHover
        draggable
        theme="colored"
      />
    </BrowserRouter>
  );
}

export default App;
