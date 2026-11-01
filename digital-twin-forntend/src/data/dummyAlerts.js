
export const dummyAlerts = [
  {
    id: "5821e38c-b3cf-4bd7-ac06-8f5053af7833",
    message: "Person detected with no safety equipment.",
    inference_analysis: "The start of the alert: 2025-10-31 20:25:26.677595, the end of the alert: 2025-10-31 20:26:07.617844.\n        Camera name: Raspberyy pi cam. \n        Detection class: NO-Safety Vest.\n        Duration: 42.940249\n        Location: [Longitude: 0E-8, Latitude: 0E-8]\n        ",
    llm_response:
      "On October 31, 2025, from 20:25:26 to 20:26:07, the Raspberry Pi camera detected a person without a safety vest at the location with coordinates [Longitude: 0E-8, Latitude: 0E-8]. The duration of the violation was 42.940249 seconds.",
    severity: "medium",
    latitude: "0.00000000",
    longitude: "0.00000000",
    detection_class: "Person",
    confidence: 0.552260160446167,
    camera_id: "b8c373c0-b431-4b75-b925-7615f0a82dd2",
    camera_name: "Raspberyy pi cam",
    video_url: null,
    alert_analysis: "complete",
    start_time: "2025-10-29T19:16:27.145757",
    end_time: "2025-10-29T19:16:34.629748",
    duration: 9.483991,
    is_resolved: false,
    is_active: true,
    assigned_cameras_count: 0,
    assigned_cameras_list: [],
    devices: [
      {
        id: "7b5d9eba-1fcb-4ddf-9b0f-3186234934d4",
        alert_id: "ae95fa61-c748-41d3-bb98-036e411c9bdf",
        camera: {
          id: "e733096d-0e3f-4d2c-8db2-67326b08380c",
          name: "Laptop Webcam",
          model: "SC-500",
          manufacturer: "CamCorp",
          serial_number: "Prov status testing",
          edge_url: "http://192.168.0.102:5001",
          latitude: "15.80926271",
          longitude: "78.03796143",
          altitude: 25.0,
          is_active: true,
          camera_type: "SECURITY",
          installation_date: "2025-07-20"
        },
        camera_name: "Laptop Webcam",
        video_url: "stream_url",
        status: "recording",
        recorded_at: "2025-10-29T19:16:27.145757",
        alert_generated: "true"
      },
      {
        id: "d0dfb01e-ed47-49e6-824f-61698dbd0117",
        alert_id: "ae95fa61-c748-41d3-bb98-036e411c9bdf",
        camera: {
          id: "b8c373c0-b431-4b75-b925-7615f0a82dd2",
          name: "Raspberyy pi cam",
          model: "SC-500",
          manufacturer: "CamCorp",
          serial_number: "Testing Device",
          edge_url: "http://192.168.0.103:5001",
          latitude: "15.80923412",
          longitude: "78.03797464",
          altitude: 25.0,
          is_active: true,
          camera_type: "SECURITY",
          installation_date: "2025-07-20"
        },
        camera_name: "Raspberyy pi cam",
        video_url: "/media/media/2025/10/29/alert_ae95fa61-c748-41d3-bb98-036e411c9bdf_device_Raspberyy_pi_cam.mp4",
        status: "uploaded",
        recorded_at: "2025-10-29T19:16:27.145757",
        alert_generated: "false"
      }
    ]
  },
  // second dummy alert (similar structure)
  {
    id: "580332c2-866c-4bb6-864e-e6f395c323b7",
    message: "Person detected with no safety equipment.",
    inference_analysis: "The start of the alert: 2025-10-31 20:25:26.677595, the end of the alert: 2025-10-31 20:26:07.617844.\n        Camera name: Raspberyy pi cam. \n        Detection class: NO-Safety Vest.\n        Duration: 42.940249\n        Location: [Longitude: 0E-8, Latitude: 0E-8]\n        ",
    llm_response:
      "On October 31, 2025, from 20:25:26 to 20:26:07, the Raspberry Pi camera detected a person without a safety vest at the location with coordinates [Longitude: 0E-8, Latitude: 0E-8]. The duration of the violation was 42.940249 seconds.",
    severity: "medium",
    latitude: "0.00000000",
    longitude: "0.00000000",
    detection_class: "Person",
    confidence: 0.552260160446167,
    camera_id: "b8c373c0-b431-4b75-b925-7615f0a82dd2",
    camera_name: "Raspberyy pi cam",
    video_url: null,
    alert_analysis: "complete",
    start_time: "2025-10-29T19:16:27.145757",
    end_time: "2025-10-29T19:16:34.629748",
    duration: 9.483991,
    is_resolved: false,
    is_active: true,
    assigned_cameras_count: 0,
    assigned_cameras_list: [],
    devices: [
      {
        id: "7b5d9eba-1fcb-4ddf-9b0f-3186234934d4",
        alert_id: "ae95fa61-c748-41d3-bb98-036e411c9bdf",
        camera: {
          id: "e733096d-0e3f-4d2c-8db2-67326b08380c",
          name: "Laptop Webcam",
          model: "SC-500",
          manufacturer: "CamCorp",
          serial_number: "Prov status testing",
          edge_url: "http://192.168.0.102:5001",
          latitude: "15.80926271",
          longitude: "78.03796143",
          altitude: 25.0,
          is_active: true,
          camera_type: "SECURITY",
          installation_date: "2025-07-20"
        },
        camera_name: "Laptop Webcam",
        video_url: "stream_url",
        status: "recording",
        recorded_at: "2025-10-29T19:16:27.145757",
        alert_generated: "true"
      },
      {
        id: "d0dfb01e-ed47-49e6-824f-61698dbd0117",
        alert_id: "ae95fa61-c748-41d3-bb98-036e411c9bdf",
        camera: {
          id: "b8c373c0-b431-4b75-b925-7615f0a82dd2",
          name: "Raspberyy pi cam",
          model: "SC-500",
          manufacturer: "CamCorp",
          serial_number: "Testing Device",
          edge_url: "http://192.168.0.103:5001",
          latitude: "15.80923412",
          longitude: "78.03797464",
          altitude: 25.0,
          is_active: true,
          camera_type: "SECURITY",
          installation_date: "2025-07-20"
        },
        camera_name: "Raspberyy pi cam",
        video_url: "/media/media/2025/10/29/alert_ae95fa61-c748-41d3-bb98-036e411c9bdf_device_Raspberyy_pi_cam.mp4",
        status: "uploaded",
        recorded_at: "2025-10-29T19:16:27.145757",
        alert_generated: "false"
      }
    ]
  }
];

export default dummyAlerts;
