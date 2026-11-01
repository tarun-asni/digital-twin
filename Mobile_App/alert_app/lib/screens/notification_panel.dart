import 'package:flutter/material.dart';
import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import '../models/alert.dart';


// NOTIFICATION PANEL SCREEN (SIMULATED POLLING EVERY 10s)
class NotificationPanel extends StatefulWidget {
  const NotificationPanel({super.key});

  @override
  _NotificationPanelState createState() => _NotificationPanelState();
}

class _NotificationPanelState extends State<NotificationPanel> {
  List<Alert> recentAlerts = [];
  Timer? timer;

  // Use the dart-defined DJANGO_BASE_URL if available, otherwise fallback
  final String? djangoBaseUrl = const String.fromEnvironment('DJANGO_BASE_URL');
  late final String apiUrl;

  @override
  void initState() {
    super.initState();
    // Initialize apiUrl here using djangoBaseUrl
    apiUrl = '${djangoBaseUrl ?? 'http://192.168.29.224:8000'}/command-center/cc-alerts/alerts/';
    fetchAlerts();
    timer = Timer.periodic(Duration(seconds: 10), (_) => fetchAlerts());
  }

  Future<void> fetchAlerts() async {
    try {
      final response = await http.get(Uri.parse(apiUrl));
      print('Response Code: ${response.statusCode}');
      print('Response Body: ${response.body}');

      if (response.statusCode == 200) {
        List jsonData = json.decode(response.body);
        setState(() {
          recentAlerts = jsonData.map((e) => Alert.fromJson(e)).toList();
          // Sort by timestamp for recent alerts display (most recent first)
          recentAlerts.sort((a, b) => b.timestamp.compareTo(a.timestamp));
        });
      } else {
        print('Failed to load alerts with status code: ${response.statusCode}');
      }
    } catch (e) {
      print('Error fetching alerts: $e');
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (recentAlerts.isEmpty) {
      return Center(child: Text('No recent alerts to display.'));
    }
    return ListView.builder(
      itemCount: recentAlerts.length,
      itemBuilder: (context, index) {
        final alert = recentAlerts[index];
        // Format the DateTime object directly
        String formattedTime = DateFormat('hh:mm:ss a').format(alert.timestamp);

        return Card(
          margin: EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          child: ListTile(
            leading: Icon(Icons.info_outline, color: Colors.orange),
            title: Text('${alert.detectionClass} - ${alert.severity}'),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Severity: ${alert.severity}'),
                Text('Confidence: ${alert.confidence.toStringAsFixed(1)}%'), 
                Text('Timestamp: $formattedTime'), 
              ],
            ),
            onTap: () => showDialog(
              context: context,
              builder: (_) => AlertDialog(
                title: Text('Alert Details'),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('ID: ${alert.id}'),
                    Text('Message: ${alert.message}'),
                    Text('Severity: ${alert.severity}'),
                    Text('Class: ${alert.detectionClass}'),
                    Text('Confidence: ${alert.confidence.toStringAsFixed(1)}%'),
                    // Format the DateTime object for full display
                    Text('Timestamp: ${DateFormat('yyyy-MM-dd hh:mm:ss a').format(alert.timestamp)}'),
                    if (alert.cameraEdgeUrl != null) Text('Camera Edge URL: ${alert.cameraEdgeUrl}'),
                    if (alert.mediaUrl != null)
                      // You can add a button/link to play video here if video_player is integrated
                      Text('Media URL: ${alert.mediaUrl}'),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}