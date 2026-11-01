import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';


Future<void> openGoogleMapsRoute(double destLat, double destLng) async {
  try {
    Position position = await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );

    final double currentLat = position.latitude;
    final double currentLng = position.longitude;

    final Uri googleMapUri = Uri.parse(
      'https://www.google.com/maps/dir/?api=1'
      '&origin=$currentLat,$currentLng'
      '&destination=$destLat,$destLng'
      '&travelmode=walking',
    );

    if (await canLaunchUrl(googleMapUri)) {
      await launchUrl(googleMapUri, mode: LaunchMode.externalApplication);
    } else {
      throw 'Could not launch Google Maps';
    }
  } catch (e) {
    print('Error opening Google Maps: $e');
  }
}


Future<void> requestLocationPermission() async {
  LocationPermission permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied ||
      permission == LocationPermission.deniedForever) {
    await Geolocator.requestPermission();
  }
}
