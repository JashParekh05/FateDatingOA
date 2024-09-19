import 'dart:convert';
import 'package:http/http.dart' as http;

Future<List<String>> fetchRestaurants() async {
  final url = 'https://drive.google.com/uc?export=download&id=1uN_gk2oJ5F4JMAsbjThTmER3LffulsZ2';
  final response = await http.get(Uri.parse(url));

  if (response.statusCode == 200) {
    final List<dynamic> data = jsonDecode(response.body);
    return List<String>.from(data.map((restaurant) => restaurant['name']));
  } else {
    throw Exception('Failed to load restaurants');
  }
}
