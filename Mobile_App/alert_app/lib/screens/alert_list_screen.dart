import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/alert.dart';
import '../locationHelper/geolocation_helper.dart';


// ALERT LIST TAB - MODIFIED FOR DATE GROUPING
class AlertListScreen extends StatefulWidget {
  const AlertListScreen({super.key});

  @override
  _AlertListScreenState createState() => _AlertListScreenState();
}

class _AlertListScreenState extends State<AlertListScreen> {
  late Future<Map<String, List<Alert>>> groupedAlertsFuture; 

  // Use the dart-defined DJANGO_BASE_URL if available, otherwise fallback
  final String? djangoBaseUrl = const String.fromEnvironment('DJANGO_BASE_URL');
  late final String apiUrl;

  @override
  void initState() {
    super.initState();
    // Initialize apiUrl here using djangoBaseUrl
    apiUrl = '${djangoBaseUrl ?? 'http://192.168.29.224:8000'}/command-center/cc-alerts/alerts/';
    groupedAlertsFuture = fetchAndGroupAlerts(); // New function call
  }

  Future<Map<String, List<Alert>>> fetchAndGroupAlerts() async {
    final response = await http.get(Uri.parse(apiUrl));
    print('Response Code (AlertListScreen): ${response.statusCode}');
    print('Response Body (AlertListScreen): ${response.body}');

    if (response.statusCode == 200) {
      List jsonData = json.decode(response.body);
      List<Alert> allAlerts = jsonData.map((alert) => Alert.fromJson(alert)).toList();

      // Sort alerts by timestamp in descending order (most recent first)
      allAlerts.sort((a, b) => b.timestamp.compareTo(a.timestamp));

      // Group alerts by date
      Map<String, List<Alert>> grouped = {};
      for (var alert in allAlerts) {
        // Format the date for the header (e.g., "July 25, 2025 (Friday)")
        String formattedDate = DateFormat('MMMM d, yyyy (EEEE)').format(alert.timestamp); 

        // Add to the grouped map
        if (!grouped.containsKey(formattedDate)) {
          grouped[formattedDate] = [];
        }
        grouped[formattedDate]!.add(alert);
      }
      return grouped;
    } else {
      throw Exception('Failed to load alerts: Status code ${response.statusCode}');
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, List<Alert>>>(
      future: groupedAlertsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        } else if (snapshot.hasError) {
          return Center(child: Text('Error loading alerts: ${snapshot.error}'));
        } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
          return Center(child: Text('No alerts found.'));
        } else {
          final groupedAlerts = snapshot.data!;
          // Sort the dates (map keys) to ensure correct chronological order of sections
          final List<String> dates = groupedAlerts.keys.toList()
            ..sort((a, b) {
              DateTime dateA = DateFormat('MMMM d, yyyy (EEEE)').parse(a);
              DateTime dateB = DateFormat('MMMM d, yyyy (EEEE)').parse(b);
              return dateB.compareTo(dateA); // Sort dates in descending order (newest date first)
            });

          return ListView.builder(
            itemCount: dates.length, // Number of unique dates
            itemBuilder: (context, dateIndex) {
              final String date = dates[dateIndex];
              final List<Alert> alertsForDate = groupedAlerts[date]!;

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                    child: Text(
                      date, // The formatted date string
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  ListView.builder(
                    shrinkWrap: true, // Important for nested ListView
                    physics: NeverScrollableScrollPhysics(), // Important to disable inner scrolling
                    itemCount: alertsForDate.length,
                    itemBuilder: (context, alertIndex) {
                      final alert = alertsForDate[alertIndex];
                      // alert.timestamp is already a DateTime, format directly
                      String formattedTime = DateFormat('hh:mm:ss a').format(alert.timestamp);

                      return Card(
                        margin: EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        child: ListTile(
                          leading: Icon(Icons.info_outline, color: Colors.orange), // Added info icon
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
                              title: Text('Alert ID: ${alert.id}'),
                              content: Column(
                                mainAxisSize: MainAxisSize.min,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Message: ${alert.message}'),
                                  Text('Class: ${alert.detectionClass}'),
                                  Text('Severity: ${alert.severity}'),
                                  Text('Confidence: ${alert.confidence.toStringAsFixed(1)}%'), 
                                  // Format the DateTime object for full display in details
                                  Text('Timestamp: ${DateFormat('yyyy-MM-dd hh:mm:ss a').format(alert.timestamp)}'),
                                  if (alert.cameraEdgeUrl != null) Text('Camera Edge URL: ${alert.cameraEdgeUrl}'),
                                  if (alert.mediaUrl != null)
                                    Text('Media URL: ${alert.mediaUrl}'),
                                ],
                              ),
                              actions: [
                                if (alert.latitude != null && alert.longitude != null)
                                  ElevatedButton(
                                    onPressed: () => openGoogleMapsRoute(alert.latitude!, alert.longitude!),
                                    child: Text('Show Route'),
                                  ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ],
              );
            },
          );
        }
      },
    );
  }
}



