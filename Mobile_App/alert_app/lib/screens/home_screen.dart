import 'package:flutter/material.dart';
import '../locationHelper/geolocation_helper.dart';
import 'notification_panel.dart';
import 'alert_list_screen.dart';


// HOME SCREEN WITH NAVIGATION TABS
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key}); 
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    requestLocationPermission(); 
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text('Alerts Dashboard'), 
          bottom: TabBar(
            tabs: [
              Tab(text: 'Notifications'),
              Tab(text: 'Alerts List'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            NotificationPanel(),
            AlertListScreen(),
          ],
        ),
      ),
    );
  }
}



