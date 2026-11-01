// --- Alert Model (Updated for robust null handling and string-to-num conversion) ---
class Alert {
  final String id;
  final String message;
  final String severity;
  final String detectionClass;
  final double confidence;
  final DateTime timestamp; 
  final String? cameraEdgeUrl;
  final String? mediaUrl; // Can be null if no video
  final double? latitude;
  final double? longitude;

  Alert({
    required this.id,
    required this.message,
    required this.severity,
    required this.detectionClass,
    required this.confidence,
    required this.timestamp,
    this.cameraEdgeUrl,
    this.mediaUrl,
    this.latitude,
    this.longitude,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    // Safely parse values, providing defaults for null or unexpected types
    return Alert(
      id: json['id']?.toString() ?? 'unknown_id',
      message: json['message']?.toString() ?? 'No message',
      severity: json['severity']?.toString() ?? 'unknown_severity',
      detectionClass: json['detection_class']?.toString() ?? 'unknown_class', 
      // Handle confidence: try parsing as double, if it's a string, try parsing string to double
      confidence: json['confidence'] is num
          ? (json['confidence'] as num).toDouble()
          : double.tryParse(json['confidence']?.toString() ?? '') ?? 0.0,
      // The timestamp is parsed here directly into a DateTime object
      timestamp: DateTime.tryParse(json['start_time']?.toString() ?? '') ?? DateTime.now(),
      cameraEdgeUrl: json['camera_edge_url'] as String?,
      mediaUrl: json['media_url'] as String?,
      // Handle latitude: try parsing as double, if it's a string, try parsing string to double
      latitude: json['latitude'] is num
          ? (json['latitude'] as num).toDouble()
          : double.tryParse(json['latitude']?.toString() ?? ''),
      // Handle longitude: try parsing as double, if it's a string, try parsing string to double
      longitude: json['longitude'] is num
          ? (json['longitude'] as num).toDouble()
          : double.tryParse(json['longitude']?.toString() ?? ''),
    );
  }
}